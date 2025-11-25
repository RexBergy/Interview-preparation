from __future__ import annotations

import asyncio
import base64
import webbrowser
import dateutil.parser
from datetime import datetime, timedelta
from typing import Dict, Sequence, Optional

import gradio as gr
import requests
import uvicorn
from fastapi import FastAPI, Request
from googleapiclient.discovery import build
from openai import OpenAI
from pydantic import BaseModel

from agents import (
    Agent, RunResult, Runner, function_tool, CodeInterpreterTool,
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


# === Calendar Scheduling Logic ===
async def schedule_plan_on_calendar(plan: CompletePlan, start_date_val):
    """
    Iterates through the plan and schedules events on Google Calendar 
    using a best-fit algorithm to find free slots.
    """

    start = datetime.fromtimestamp(start_date_val)
    for day in plan.daily_plans:
        for task in day.tasks:
            #find the task for this day to avoid conflicts
            # then insert tasks in the calendar
            task.name
            task.description
            task.duration


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
    time_per_day: int,
    start_date: str,
    interview_date: str,
    use_calendar: bool,
    progress = gr.Progress()
) -> CompletePlan:
    
    progress(0, desc="🔍 Preparing your personalized plan...")
    
    # Build system prompt
    system_prompt = f"""
    Personalized Interview Preparation Plan for:
    - Daily Preparation Time : {time_per_day} hours
    - Start Date: {start_date}, Interview Date: {interview_date}
    """

    job_prompt = f"\nJob Description:\n{job_desc}\n"
    full_prompt = system_prompt + job_prompt

    # Encode CV
    progress(0.1, desc="📄 Processing CV...")
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
    
    feasibility_tool = feasibility_agent.as_tool(
        tool_name="feasibility_check",
        tool_description="Ensures plan is realistic given time constraints",
        custom_output_extractor=_summary_extractor
    )

    # NOTE: We REMOVED calendar tools from here to save tokens and stability
    tools = [feasibility_tool]

    writer_with_tools = writer_agent.clone(tools=tools)

    # Run writer
    progress(0.5, desc="✍️ Generating your personalized plan...")
    
    result = await Runner.run(
        writer_with_tools,
        [
            {"role": "assistant", "content": full_prompt},
            {"role": "user", "content": [{
                "type": "input_file",
                "file_data": f"data:application/pdf;base64,{cv_base64}",
                "filename": cv_file.name,
            }]}
        ]
    )
    
    plan = result.final_output_as(CompletePlan)
    progress(0.9, desc="✅ Plan generated!")

    # === Post-Processing: Calendar Schedule ===
    if use_calendar and calendar_service:
        progress(0.95, desc="📅 Syncing to Google Calendar...")
        await schedule_plan_on_calendar(plan, start_date)
    
    progress(1.0, desc="🎉 All Done!")
    return plan


# === Gradio Interface ===
with gr.Blocks(title="Interview Prep Assistant") as demo:
    plan_state = gr.State(value=None)
    
    gr.Markdown("# Interview Preparation Assistant")
    gr.Markdown("Upload your CV and job description to get a **personalized prep plan**.")

    with gr.Row():
        with gr.Column():
            cv_input = gr.File(label="Upload CV (PDF)", file_types=[".pdf"])
            job_desc = gr.Textbox(label="Job Description", lines=8)
            role = gr.Textbox(label="Current Role")
            goals = gr.Textbox(label="Career Goals", lines=2)

        with gr.Column():
            time_available = gr.Slider(1, 8, value=2, step=1, label="Hours/Day")
            start_date = gr.DateTime(label="Start Date")
            interview_date = gr.DateTime(label="Interview Date")


    use_calendar = gr.Checkbox(label="Add tasks to Google Calendar", value=False)
    
    submit_btn = gr.Button("Generate Plan", variant="primary", size="lg")
    status_msg = gr.Markdown("")
    
    @gr.render(inputs=plan_state)
    def render_plan(plan: CompletePlan):
        if not plan:
            gr.Markdown("### Your personalized plan will appear here...")
        else:
            summary_md = f"### 📝 Summary\n{plan.short_summary}"
            gr.Markdown(value=summary_md)
            
            with gr.Group():
                for day_info in plan.daily_plans:
                    task_md = "\n".join([f"- **{t.name}**:\n {t.description}" for t in day_info.tasks])
                    with gr.Accordion(label=f"📅 Day {day_info.day}", open=False):
                        gr.Markdown(task_md)

    async def on_submit(*inputs, progress=gr.Progress()):
        (
            cv_file, job_desc_val, role_val, goals_val,
            time_per_day,
            start_date_val, interview_date_val, use_calendar_val
        ) = inputs

        # Show loading state
        yield {
            submit_btn: gr.update(value="⏳ Generating Plan...", interactive=False),
            status_msg: "🚀 Starting plan generation...",
            plan_state: None
        }

        try:
            plan = await generate_plan(
                cv_file=cv_file,
                job_desc=job_desc_val or "",
                role=role_val or "Professional",
                goals=goals_val or "Secure the role",
                time_per_day=int(time_per_day),
                start_date=str(start_date_val),
                interview_date=str(interview_date_val),
                use_calendar=use_calendar_val,
                progress=progress
            )
            
            # Success
            yield {
                submit_btn: gr.update(value="Generate Plan", interactive=True),
                status_msg: "✅ Plan generated successfully!",
                plan_state: plan
            }
            
        except Exception as e:
            # Error
            yield {
                submit_btn: gr.update(value="Generate Plan", interactive=True),
                status_msg: f"❌ **Error:** {str(e)}",
                plan_state: None
            }

    submit_btn.click(
        fn=on_submit,
        inputs=[
            cv_input, job_desc,role, goals,
            time_available,
            start_date, interview_date, use_calendar
        ],
        outputs=[submit_btn, status_msg, plan_state]
    )


if __name__ == "__main__":
    # === Mount Gradio + Run Server ===
    gr.mount_gradio_app(app, demo, path="/")
    uvicorn.run(app, host="localhost", port=8080)