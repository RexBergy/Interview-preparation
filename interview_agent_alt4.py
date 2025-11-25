from __future__ import annotations

import asyncio
import base64
import webbrowser
import re
import time
from datetime import datetime, timedelta
from dateutil import parser as date_parser  # pip install python-dateutil
from typing import Dict, Sequence, Optional, Tuple

import gradio as gr
from fastapi import FastAPI, Request
from googleapiclient.discovery import build
from openai import OpenAI

from agents import (
    Agent, RunResult, Runner, function_tool, SQLiteSession
)
from local_agents.writer import writer_agent, CompletePlan, DailyPlan, Task
from authentification import connect, fetch_token
from openai.types.responses import ResponseTextDeltaEvent

# === FastAPI & Globals ===
app = FastAPI()
calendar_service = None 

# === OpenAI Client (For direct streaming) ===
client = OpenAI()

# === OAuth Routes ===
@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    global calendar_service
    auth_url = str(request.url)
    try:
        credentials = fetch_token(auth_url)
        calendar_service = build("calendar", "v3", credentials=credentials)
        return "Calendar authentication successful! You can close this tab."
    except Exception as e:
        return f"Error: {e}"

def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ==========================================
# 🧠 LOGIC 1: The Parser (Text -> Object)
# ==========================================
def parse_markdown_to_plan(markdown_text: str) -> CompletePlan:
    """
    Converts the streamed Markdown string into a structured CompletePlan object
    so we can use it for the Calendar logic.
    """
    lines = markdown_text.split('\n')
    daily_plans = []
    current_day = 0
    current_tasks = []
    summary = "Generated Plan"

    # Regex to find tasks: "- 60 mins: **Title** - Description"
    task_pattern = re.compile(r'-\s+(\d+)\s*mins?:\s*\*\*(.*?)\*\*\s*-\s*(.*)')
    
    for line in lines:
        line = line.strip()
        
        # 1. Capture Summary
        if line.startswith("### Summary"):
            # The next non-empty line is usually the summary
            try:
                idx = lines.index(line)
                summary = lines[idx+1].strip() or lines[idx+2].strip()
            except:
                pass

        # 2. Capture Day Headers
        day_match = re.search(r'Day\s+(\d+)', line, re.IGNORECASE)
        if day_match and line.startswith('#'):
            # Save previous day
            if current_day > 0 and current_tasks:
                daily_plans.append(DailyPlan(day=current_day, tasks=current_tasks))
            
            current_day = int(day_match.group(1))
            current_tasks = []
            continue

        # 3. Capture Tasks
        match = task_pattern.match(line)
        if match:
            duration = int(match.group(1))
            name = match.group(2).strip()
            desc = match.group(3).strip()
            current_tasks.append(Task(name=name, description=desc, duration=duration))

    # Append last day
    if current_day > 0 and current_tasks:
        daily_plans.append(DailyPlan(day=current_day, tasks=current_tasks))

    return CompletePlan(short_summary=summary, daily_plans=daily_plans)


# ==========================================
# 🧠 LOGIC 2: Pre-Computation (Speed)
# ==========================================
def calculate_metrics(start_str: datetime, interview_str: datetime, hours_per_day: int) -> Tuple[int, int]:
    
    delta = interview_str - start_str
    days = delta.days
    return days, days * hours_per_day

def pre_fetch_search(role: str, job_desc: str) -> str:
    """Runs a targeted search BEFORE the AI starts writing."""
    # Simulating the search tool for speed. 
    # In production, call your WebSearchTool().run(query) here.
    return f"Key interview topics for {role}: System Design, Scalability, Leadership Principles."


# ==========================================
# 🧠 LOGIC 3: Smart Scheduler (Conflict Free)
# ==========================================
async def smart_schedule_plan(plan: CompletePlan, start_date_str: datetime, preferred_hour: int, progress=gr.Progress()):
    """
    Fetches existing events -> Finds gaps -> Inserts tasks.
    """
    if not calendar_service:
        return "❌ Calendar not authenticated."

    # 1. Setup Time Boundaries
    cursor = start_date_str.astimezone()

    # Align to preferred hour
    if cursor.hour < preferred_hour:
        cursor = cursor.replace(hour=preferred_hour, minute=0, second=0)

    # Fetch busy slots (Batch)
    end_horizon = cursor + timedelta(days=len(plan.daily_plans) + 5)
    
    print("📅 Fetching existing calendar events...")
    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=cursor.isoformat(), 
        timeMax=end_horizon.isoformat(), 
        singleEvents=True, 
        orderBy='startTime'
    ).execute()
    
    busy_slots = []
    for e in events_result.get('items', []):
        if 'dateTime' in e['start']:
            busy_slots.append((
                date_parser.parse(e['start']['dateTime']),
                date_parser.parse(e['end']['dateTime'])
            ))

    # 2. Tetris Logic
    total_tasks = sum(len(d.tasks) for d in plan.daily_plans)
    tasks_done = 0

    for day in plan.daily_plans:
        # Start looking at the preferred hour of this calculated day
        day_target = cursor.replace(hour=preferred_hour, minute=0)
        if day_target < cursor: 
            day_target += timedelta(days=1)
        cursor = day_target

        for task in day.tasks:
            scheduled = False
            while not scheduled:
                proposed_end = cursor + timedelta(minutes=task.duration)
                
                # Check Overlaps
                conflict = False
                for (b_start, b_end) in busy_slots:
                    # Simple overlap logic
                    if (cursor < b_end) and (proposed_end > b_start):
                        conflict = True
                        cursor = b_end + timedelta(minutes=5) # Jump over conflict
                        break
                
                if not conflict:
                    # Insert
                    body = {
                        "summary": f"🎯 Prep: {task.name}",
                        "description": task.description,
                        "start": {"dateTime": cursor.isoformat()},
                        "end": {"dateTime": proposed_end.isoformat()},
                    }
                    try:
                        calendar_service.events().insert(calendarId='primary', body=body).execute()
                        time.sleep(0.5) # Rate limit protection
                    except Exception as e:
                        print(f"Calendar Error: {e}")

                    cursor = proposed_end + timedelta(minutes=10) # Break
                    scheduled = True
                    tasks_done += 1
                    progress((tasks_done / total_tasks), desc=f"📅 Scheduling: {task.name}")

    return "✅ All tasks scheduled successfully!"


# ==========================================
# 🌊 UI & STREAMING LOGIC
# ==========================================

async def generate_stream(
    cv_file, job_desc, role, goals, time_per_day, start_date, interview_date, use_cal, pref_time,
    progress=gr.Progress()
):
    """
    Main handler: Streams text -> Parses -> Syncs Calendar
    """
    # Initialize "Empty" states for the outputs
    # Order: [plan_display, status_msg, submit_btn, step_2_col, step_3_col]
    
    # 1. Switch Views Immediately (Hide Step 2, Show Step 3)
    yield (
        "",           # plan_display
        "🚀 Starting analysis...",      # status_msg
        gr.update(interactive=False),   # submit_btn
        gr.update(visible=False),       # step_2_col
        gr.update(visible=True)         # step_3_col
    )

    # 2. Validation & Setup
    if not cv_file: 
        raise gr.Error("Please upload a CV.")
    
    start_dt = datetime.fromtimestamp(float(start_date)) 
    interview_dt = datetime.fromtimestamp(float(interview_date)) 

    if use_cal and not calendar_service:
        auth_url = connect()
        webbrowser.open(auth_url)
        max_wait = 60
        for i in range(max_wait):
            if calendar_service:
                break
            await asyncio.sleep(1)
            if i % 5 == 0:
                progress(0.2 + (i/max_wait) * 0.2, desc=f"⏳ Waiting for authentication... ({60-i}s)")
        
        if not calendar_service:
            raise ValueError("Calendar authentication timed out.")

    progress(0.1, desc="⚡ Calculating Metrics...")
    yield (
        "",           # plan_display
        " Calculating Metrics...",      # status_msg
        gr.update(interactive=False),   # submit_btn
        gr.update(visible=False),       # step_2_col
        gr.update(visible=True)         # step_3_col
    )
    days, total_hours = calculate_metrics(start_dt, interview_dt, time_per_day)
    search_context = pre_fetch_search(role, job_desc)

    # 3. Construct Prompt
    system_prompt = f"""
    CONTEXT:
    - Role: {role}
    - Goal: {goals}
    - Available: {days} days, {total_hours} total hours ({time_per_day} hours/day).
    
    SEARCH INTEL:
    {search_context}
    
    JOB DESCRIPTION:
    {job_desc}
    
    INSTRUCTIONS:
    Write a preparation plan in STRICT MARKDOWN. 
    """
    
    # 4. Stream Generation
    progress(0.2, desc="✍️ Writing Plan...")
    full_response = ""
    
    result = Runner.run_streamed(writer_agent, system_prompt)

    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            # content = chunk.choices[0].delta.content
            full_response += event.data.delta
            
            # YIELD UPDATE: Must match the output list order exactly
            yield (
                full_response,                  # plan_display
                "✍️ AI is writing...",           # status_msg
                gr.update(interactive=False),   # submit_btn
                gr.update(visible=False),       # step_2_col
                gr.update(visible=True)         # step_3_col
            )

    # 5. Parse & Post-Processing
    progress(0.8, desc="⚙️ Parsing Plan...")
    plan_object = parse_markdown_to_plan(full_response)
    
    # 6. Calendar Sync
    final_status = "✅ Plan Generated Successfully!"
    if use_cal:
        final_status = await smart_schedule_plan(plan_object, start_dt, pref_time, progress=progress)
    
    # Final Yield
    yield (
        full_response,                  # plan_display
        final_status,                   # status_msg
        gr.update(interactive=True, value="🚀 Generate Plan"),   # Re-enable button
        gr.update(visible=False),       # step_2_col
        gr.update(visible=True)         # step_3_col
    )

# ==========================================
# 🖥️ GRADIO UI (Wizard)
# ==========================================
css = ".container { max-width: 800px; margin: auto; } .btn-primary { background-color: #2563eb; color: white; }"

with gr.Blocks(title="Interview Agent", css=css) as demo:
    # State management
    current_step = gr.State(0)

    gr.Markdown("# 🚀 AI Interview Coach", elem_classes="text-center")

    # --- Step 0: CV ---
    with gr.Column(visible=True) as step_0_col:
        gr.Markdown("### Step 1: Upload CV")
        cv_input = gr.File(label="Your CV (PDF)")
        s0_next = gr.Button("Next ➡️")

    # --- Step 1: Details ---
    with gr.Column(visible=False) as step_1_col:
        gr.Markdown("### Step 2: Target Role")
        job_desc = gr.Textbox(label="Job Description", lines=5)
        with gr.Row():
            role = gr.Textbox(label="Role Title")
            goals = gr.Textbox(label="Key Goals")
        with gr.Row():
            s1_back = gr.Button("⬅️ Back")
            s1_next = gr.Button("Next ➡️", variant="primary")

    # --- Step 2: Logistics ---
    with gr.Column(visible=False) as step_2_col:
        gr.Markdown("### Step 3: Logistics")
        with gr.Row():
            start_date = gr.DateTime(label="Start Date")
            interview_date = gr.DateTime(label="Interview Date")
        
        with gr.Row():
            time_per_day = gr.Slider(1, 12, value=2, label="Hours/Day")
            # Dropdown for preferred time (Best UX)
            pref_time = gr.Dropdown(
                choices=[("Morning (9AM)", 9), ("Afternoon (2PM)", 14), ("Evening (6PM)", 18)],
                value=18, label="Preferred Study Time"
            )

        use_cal = gr.Checkbox(label="📅 Auto-Sync to Google Calendar")
        status_msg = gr.Markdown("")
        
        with gr.Row():
            s2_back = gr.Button("⬅️ Back")
            submit_btn = gr.Button("🚀 Generate Plan", variant="primary")

    # --- Step 3: Results (Streaming) ---
    with gr.Column(visible=False) as step_3_col:
        gr.Markdown("## 📝 Your Personalized Plan")
        status_msg = gr.Markdown("")
        plan_display = gr.Markdown("Thinking...")


    # --- Wiring ---
    def nav(curr, direction):
        nxt = curr + direction
        return (nxt, gr.update(visible=nxt==0), gr.update(visible=nxt==1), gr.update(visible=nxt==2), gr.update(visible=nxt==3))

    s0_next.click(lambda c: nav(c, 1), inputs=[current_step], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    s1_next.click(lambda c: nav(c, 1), inputs=[current_step], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    s1_back.click(lambda c: nav(c, -1), inputs=[current_step], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    s2_back.click(lambda c: nav(c, -1), inputs=[current_step], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    
    # restart_btn.click(lambda: (0, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), ""),
    #                   outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col, plan_display])

    # --- Submission ---
    submit_btn.click(
        fn=generate_stream,
        inputs=[cv_input, job_desc, role, goals, time_per_day, start_date, interview_date, use_cal, pref_time],
        outputs=[plan_display, status_msg, submit_btn, step_2_col, step_3_col] 
    )

if __name__ == "__main__":
    gr.mount_gradio_app(app, demo, path="/")
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)