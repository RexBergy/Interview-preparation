from __future__ import annotations

import asyncio
import base64
import webbrowser
from typing import Dict, Sequence, Optional

import gradio as gr
import requests
import uvicorn
from fastapi import FastAPI, Request
from googleapiclient.discovery import build
from openai import OpenAI
from pydantic import BaseModel

from agents import (
    Agent, RunResult, Runner, WebSearchTool, function_tool, CodeInterpreterTool,
    SQLiteSession, custom_span
)
from local_agents.writer import writer_agent, CompletePlan
from local_agents.progress_judge import feasibility_agent
from local_agents.personality_judge import personality_judge_agent
from authentification import connect, fetch_token


# === Models ===
class EventDateTime(BaseModel):
    dateTime: str
    timeZone: str


# === FastAPI App & Global State ===
app = FastAPI()
calendar_service = None  # Will hold authenticated Google Calendar service


async def _summary_extractor(run_result: RunResult) -> str:
    """Extracts summary text from sub-agent results."""
    return str(run_result.final_output.summary)

# === OAuth2 Callback ===
@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    global calendar_service
    auth_url = str(request.url)
    print(f"[OAuth] Callback received: {auth_url}")

    try:
        credentials = fetch_token(auth_url)
        calendar_service = build("calendar", "v3", credentials=credentials)
        print("[OAuth] Successfully authenticated with Google Calendar")
        return {"status": "success", "message": "Calendar access granted!"}
    except Exception as e:
        print(f"[OAuth] Authentication failed: {e}")
        return {"status": "error", "message": str(e)}


# === OpenAI & Tools ===
client = OpenAI()
session = SQLiteSession("in-memory")


def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# === Core Agent Tools ===
@function_tool
def create_event(name: str, start: EventDateTime, end: EventDateTime) -> str:
    """
    Create a calendar event in the user's primary Google Calendar.
    """
    if not calendar_service:
        raise ValueError("Google Calendar not authenticated yet.")

    event = {
        "summary": name,
        "start": start.model_dump(mode="json"),
        "end": end.model_dump(mode="json"),
    }
    try:
        calendar_service.events().insert(calendarId="primary", body=event).execute()
        print(f"[Calendar] Event created: {name}")
        return f"Successfully created event {name}, start {start.dateTime}, end {end.dateTime}"
    except Exception as e:
        print(f"[Calendar] Failed to create event: {e}")
        return f"Failed to create event {name}, start {start.dateTime}, end {end.dateTime}. Error : {e}"

@function_tool
def check_schedule(start: EventDateTime, end: EventDateTime) -> str:
    """
    Checks the user's calendar to find available timslot
    Include the timezone offset in the time as well
    """
    # # Fetch events
    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=start.dateTime,
        timeMax=end.dateTime,
        singleEvents=True,
        timeZone=start.timeZone,
        orderBy='startTime'
    ).execute()

    print("Checked schedule")
    return events_result


# === Plan Generation Logic ===
def format_plan_for_ui(plan: CompletePlan) -> str:
    lines = [f"### Summary\n{plan.short_summary}\n"]
    for day in plan.daily_plans:
        lines.append(f"#### Day {day.day}")
        for task in day.tasks:
            lines.append(f"- **{task.name}**: {task.description}")
        lines.append("")
    return "\n".join(lines)

async def generate_plan(
    cv_file,
    job_desc: str,
    role: str,
    goals: str,
    preferred_start_hour: int,
    time_per_day: int,
    start_date: str,
    interview_date: str,
    use_calendar: bool,
    progress = gr.Progress()
) -> CompletePlan:
    
    progress(0, desc="🔍 Preparing your personalized plan...")

    start_date = datetime.fromtimestamp(float(start_date))
    interview_date = datetime.fromtimestamp(float(interview_date))

    total_days = interview_date - start_date
    total_days = total_days.days



    
    # Build system prompt
    system_prompt = f"""
    Personalized Interview Preparation Plan for:
    - Daily Preparation Time : {time_per_day} hours
    - Number of preparation days {total_days}
    """

    
    job_prompt = f"\nJob Description:\n{job_desc}\n"
    full_prompt = system_prompt + job_prompt

    # Encode CV
    progress(0.1, desc="📄 Processing CV...")
    if cv_file is None:
        raise ValueError("No CV uploaded.")
    cv_base64 = file_to_base64(cv_file.name)

    # Optional: Trigger OAuth if calendar is requested
    if use_calendar and not calendar_service:
        progress(0.2, desc="🔐 Authenticating with Google Calendar...")
        auth_url = connect()
        print(f"[Auth] Opening browser for Google login: {auth_url}")
        webbrowser.open(auth_url)
        gr.Warning("Please complete Google login in the opened browser tab.")
        
        # Wait for authentication with timeout
        max_wait = 60
        for i in range(max_wait):
            if calendar_service:
                break
            await asyncio.sleep(1)
            if i % 5 == 0:  # Update every 5 seconds
                progress(0.2 + (i/max_wait) * 0.2, desc=f"⏳ Waiting for authentication... ({60-i}s)")
        
        if not calendar_service:
            raise ValueError("Calendar authentication timed out. Please try again.")

    # === Writer Agent with Tools ===
    progress(0.4, desc="🤖 Initializing AI agents...")
    
    # feasibility_tool = feasibility_agent.as_tool(
    #     tool_name="feasibility_check",
    #     tool_description="Ensures plan is realistic given time constraints",
    #     custom_output_extractor=_summary_extractor
    # )

    # tools = [feasibility_tool]
    # # if use_calendar:
    # #     tools.extend([check_schedule])

    # writer_with_tools = writer_agent.clone(tools=tools)

    # Run writer
    progress(0.5, desc="✍️ Generating your personalized plan...")
    
    result = await Runner.run(
        writer_agent,
        [
            {"role": "assistant", "content": full_prompt},
            {"role": "user", "content": [{
                "type": "input_file",
                "file_data": f"data:application/pdf;base64,{cv_base64}",
                "filename": cv_file.name,
            }]}
        ]
    )

    #plan = result.final_output_as(CompletePlan)
    plan = result

# === NEW: Run the Python Smart Scheduler ===
    if use_calendar and calendar_service:
        progress(0.9, desc="📅 Finding free slots in your calendar...")
        
        # This runs the "Tetris" logic
        await smart_schedule_plan(plan, start_date, preferred_start_hour)

    progress(1.0, desc="✅ Plan synced to Calendar!")
    
    return plan

# async def schedule_plan_on_calendar(plan: CompletePlan, start_date, hours_per_day):
#     pass

from datetime import datetime, timedelta
import time
from dateutil import parser # Requires: pip install python-dateutil

# Helper: Pre-Search (Fast)
def pre_fetch_context(job_desc: str, role: str) -> str:
    """
    Runs a targeted search immediately using your existing tool logic 
    but WITHOUT the agent overhead.
    """
    # Construct a high-value query
    query = f"{role} interview process questions guide"
    
    # Using your existing WebSearchTool class manually
    # (Assuming it has a .run or similar method, otherwise use simple requests/duckduckgo)
    search_tool = WebSearchTool() 
    
    try:
        # We call the search tool directly!
        # Note: Check your agents.py for the exact method name (often .run, .func, or __call__)
        results = search_tool.run(query) 
        return results
    except Exception as e:
        print(f"Search failed: {e}")
        return "No search results available."

async def smart_schedule_plan(plan: CompletePlan, start_date_iso: datetime, preferred_hour: int):
    """
    1. Fetches ALL existing events for the plan duration (Batch Read).
    2. Finds free slots using Python logic (No AI guessing).
    3. Inserts events safely.
    """
    if not calendar_service:
        raise ValueError("Google Calendar not authenticated.")

    # 1. Setup Time Boundaries
    # ---------------------------------------------------------
    # try:
    #     print(float(start_date_iso),type(float(start_date_iso)))
    #     current_cursor = datetime.fromtimestamp(float(start_date_iso)).astimezone()
    #     print("Real start date")
    # except:
    #     current_cursor = datetime.now().astimezone()
    #     print("now start date")

    current_cursor = start_date_iso.astimezone()

    # Align cursor to the user's preferred start hour (e.g., 6 PM)
    if current_cursor.hour < preferred_hour:
        current_cursor = current_cursor.replace(hour=preferred_hour, minute=0, second=0)

    # Calculate end of plan (approximate) to fetch existing events
    # We add 2 extra days of buffer just in case
    total_days = len(plan.daily_plans) + 2
    end_horizon = current_cursor + timedelta(days=total_days)

    print(f"📅 Fetching existing events from {current_cursor} to {end_horizon}...")

    # 2. Batch Read: Get ALL busy slots in one API call (Fast & Error-free)
    # ---------------------------------------------------------
    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=current_cursor.isoformat(),
        timeMax=end_horizon.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    existing_events = events_result.get('items', [])
    
    # Convert existing events to simple (start, end) datetime tuples for easy math
    busy_slots = []
    for event in existing_events:
        start = event['start'].get('dateTime') or event['start'].get('date')
        end = event['end'].get('dateTime') or event['end'].get('date')
        if start and end:
            # Parse and ensure timezone awareness
            s_dt = parser.parse(start)
            e_dt = parser.parse(end)
            busy_slots.append((s_dt, e_dt))

    print(f"✅ Found {len(busy_slots)} existing busy slots.")

    # 3. Tetris Logic: Fit AI Tasks into Free Slots
    # ---------------------------------------------------------
    scheduled_count = 0
    
    for day in plan.daily_plans:
        # Reset cursor to preferred start time for the new day
        # Ensure we don't schedule in the past if 'current_cursor' is already ahead
        day_start_target = current_cursor.replace(hour=preferred_hour, minute=0, second=0)
        
        # If the cursor is already past today's start target, move to tomorrow
        if current_cursor > day_start_target:
             day_start_target = current_cursor.replace(hour=preferred_hour, minute=0, second=0) + timedelta(days=1)
        
        current_cursor = day_start_target

        for task in day.tasks:
            duration_minutes = task.duration
            task_scheduled = False
            
            # Try to find a slot for this specific task
            while not task_scheduled:
                proposed_end = current_cursor + timedelta(minutes=duration_minutes)
                
                # Check for conflicts
                conflict_found = False
                for (b_start, b_end) in busy_slots:
                    # Logic: If (Start < BusyEnd) and (End > BusyStart), they overlap
                    if current_cursor < b_end and proposed_end > b_start:
                        conflict_found = True
                        # Jump cursor to the end of this busy block + 5 min buffer
                        current_cursor = b_end + timedelta(minutes=5)
                        break # Break inner loop, try new cursor position
                
                if not conflict_found:
                    # Stop! We found a gap. Insert here.
                    await insert_calendar_event(task, current_cursor, proposed_end)
                    
                    # Update cursor for next task
                    current_cursor = proposed_end + timedelta(minutes=10) # 10 min break
                    task_scheduled = True
                    scheduled_count += 1
                    
                    # Anti-Rate-Limit: Pause slightly between writes
                    time.sleep(0.5) 
            
    return f"Successfully scheduled {scheduled_count} tasks avoiding all conflicts."

async def insert_calendar_event(task, start_dt, end_dt):
    """Helper to actually write to Google."""
    event_body = {
        "summary": f"🎯 Prep: {task.name}",
        "description": task.description,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }
    try:
        calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        print(f"Created: {task.name} at {start_dt}")
    except Exception as e:
        print(f"Error creating event: {e}")


# === Gradio Interface (Wizard Style) ===
css = """
.container { max-width: 800px; margin: auto; }
.btn-primary { background-color: #2563eb !important; color: white !important; }
"""

with gr.Blocks(title="Interview Prep Assistant", css=css) as demo:
    # Global State to hold the current step index
    current_step = gr.State(value=0)
    plan_state = gr.State(value=None)
    
    gr.Markdown("# 🎯 Interview Preparation Assistant", elem_classes="text-center")
    
    # ================= STEP 0: CV Upload =================
    with gr.Column(visible=True) as step_0_col:
        gr.Markdown("### Step 1: Who are you?")
        gr.Markdown("Start by uploading your CV so we can analyze your current profile.")
        
        cv_input = gr.File(label="Upload CV (PDF)", file_types=[".pdf"], height=150)
        
        with gr.Row():
            gr.Markdown("") # Spacer
            s0_next = gr.Button("Next ➡️", variant="primary")

    # ================= STEP 1: Context & Job =================
    with gr.Column(visible=False) as step_1_col:
        gr.Markdown("### Step 2: What is the target?")
        gr.Markdown("Tell us about the job you are applying for and your goals.")
        
        job_desc = gr.Textbox(label="Job Description", lines=8, placeholder="Paste the full job description here...")
        with gr.Row():
            role = gr.Textbox(label="Current Role", placeholder="e.g. Senior Backend Engineer")
            goals = gr.Textbox(label="Specific Goals", placeholder="e.g. Improve system design skills")

        with gr.Row():
            s1_back = gr.Button("⬅️ Back")
            s1_next = gr.Button("Next ➡️", variant="primary")

    # ================= STEP 2: Logistics =================
    with gr.Column(visible=False) as step_2_col:
        gr.Markdown("### Step 3: Logistics")
        gr.Markdown("When can you prepare and when is the big day?")
        
        with gr.Row():
            start_date = gr.DateTime(label="Start Preparation Date", include_time=True)
            interview_date = gr.DateTime(label="Interview Date", include_time=True)
        
        time_available = gr.Slider(1, 12, value=2, step=1, label="Hours Available per Day")
        preferred_time = gr.Dropdown(
            choices=[
                ("🌅 Early Morning (6 AM - 9 AM)", 6),
                ("☀️ Morning (9 AM - 12 PM)", 9),
                ("🥪 Lunch Break (12 PM - 2 PM)", 12),
                ("☕ Afternoon (2 PM - 5 PM)", 14),
                ("🌇 Evening (5 PM - 8 PM)", 17),
                ("🌙 Late Night (8 PM - 11 PM)", 20)
            ],
            value=17, # Default to 5 PM
            label="When do you prefer to prepare?",
            info="The AI will try to schedule your sessions during this window."
        )
        use_calendar = gr.Checkbox(label="📅 Add tasks directly to my Google Calendar", value=False)

        status_msg = gr.Markdown("")
        
        with gr.Row():
            s2_back = gr.Button("⬅️ Back")
            submit_btn = gr.Button("🚀 Generate Plan", variant="primary", size="lg")

    # ================= STEP 3: Results =================
    with gr.Column(visible=False) as step_3_col:
        gr.Markdown("## ✅ Your Personalized Plan")
        restart_btn = gr.Button("🔄 Start Over")
        
        @gr.render(inputs=plan_state)
        def render_plan(plan: CompletePlan):
            if not plan:
                gr.Markdown("Waiting for generation...")
            else:
                summary_md = f"### 📝 Executive Summary\n{plan.short_summary}"
                gr.Markdown(value=summary_md)
                
                with gr.Group():
                    for day_info in plan.daily_plans:
                        task_md = "\n".join([f"- **{t.name}** ({t.duration}m):\n {t.description}" for t in day_info.tasks])
                        with gr.Accordion(label=f"📅 Day {day_info.day}", open=False):
                            gr.Markdown(task_md)

    # ================= Navigation Logic =================
    def navigate(curr_step, direction):
        new_step = curr_step + direction
        # Return update for current_step state, followed by visibility updates for columns 0, 1, 2, 3
        return (
            new_step,
            gr.update(visible=new_step == 0),
            gr.update(visible=new_step == 1),
            gr.update(visible=new_step == 2),
            gr.update(visible=new_step == 3)
        )

    # Helper to validate Step 0
    def validate_step_0(cv, curr_step):
        if cv is None:
            raise gr.Error("Please upload a CV before proceeding.")
        return navigate(curr_step, 1)

    # Helper to validate Step 1
    def validate_step_1(job, curr_step):
        if not job or len(job.strip()) < 10:
            raise gr.Error("Please enter a valid Job Description.")
        return navigate(curr_step, 1)

    # Wiring Buttons
    s0_next.click(validate_step_0, inputs=[cv_input, current_step], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    
    s1_back.click(navigate, inputs=[current_step, gr.Number(-1, visible=False)], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    s1_next.click(validate_step_1, inputs=[job_desc, current_step], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    
    s2_back.click(navigate, inputs=[current_step, gr.Number(-1, visible=False)], outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col])
    
    restart_btn.click(lambda: (0, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), None),
                      inputs=None,
                      outputs=[current_step, step_0_col, step_1_col, step_2_col, step_3_col, plan_state])

    # ================= Submission Logic =================
    async def on_submit(cv_file, job_desc_val, role_val, goals_val, prefered_start_hour, time_per_day, start_date_val, interview_date_val, use_calendar_val, progress=gr.Progress()):
        # 1. UI Update: Disable button
        yield {
            submit_btn: gr.update(value="⏳ Generating Plan...", interactive=False),
            status_msg: "🚀 Analyzing Agent starting...",
            step_0_col: gr.update(visible=False),
            step_1_col: gr.update(visible=False),
            step_2_col: gr.update(visible=True), # Keep visible during loading
            step_3_col: gr.update(visible=False)
        }

        try:
            plan = await generate_plan(
                cv_file=cv_file,
                job_desc=job_desc_val or "",
                role=role_val or "Professional",
                goals=goals_val or "Secure the role",
                preferred_start_hour=prefered_start_hour,
                time_per_day=int(time_per_day),
                start_date=str(start_date_val),
                interview_date=str(interview_date_val),
                use_calendar=use_calendar_val,
                progress=progress
            )
            
            # 2. Success: Move to Step 3
            yield {
                submit_btn: gr.update(value="🚀 Generate Plan", interactive=True),
                status_msg: "✅ Done!",
                plan_state: plan,
                current_step: 3,
                step_2_col: gr.update(visible=False),
                step_3_col: gr.update(visible=True)
            }
            
        except Exception as e:
            # 3. Error: Stay on Step 2
            yield {
                submit_btn: gr.update(value="🚀 Generate Plan", interactive=True),
                status_msg: f"❌ **Error:** {str(e)}",
                plan_state: None,
                step_2_col: gr.update(visible=True),
                step_3_col: gr.update(visible=False)
            }

    submit_btn.click(
            fn=on_submit,
            inputs=[
                cv_input, job_desc, role, goals, preferred_time,
                time_available,
                start_date, interview_date, use_calendar
            ],
            # FIX: Added step_0_col and step_1_col here because on_submit updates them
            outputs=[submit_btn, status_msg, plan_state, current_step, step_0_col, step_1_col, step_2_col, step_3_col]
        )


if __name__ == "__main__":
    # === Mount Gradio + Run Server ===
    gr.mount_gradio_app(app, demo, path="/")
    uvicorn.run(app, host="localhost", port=8080)