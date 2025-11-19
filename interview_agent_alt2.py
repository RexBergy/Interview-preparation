from __future__ import annotations
import asyncio
import base64
from typing import Dict, Sequence
import gradio as gr
from openai import OpenAI
from agents import (
    Agent, RunResult, Runner, function_tool, CodeInterpreterTool,
    SQLiteSession, custom_span
)
from local_agents.cv_plus_job import cv_job_reader, CandidateProfile
from local_agents.planner import planning_agent, InterviewSearchPlan, InterviewSearchItem
from local_agents.material_search import search_agent
from local_agents.writer import writer_agent, CompletePlan
from local_agents.progress_judge import feasibility_agent
from local_agents.personality_judge import personality_judge_agent
from pydantic import BaseModel
import requests
import webbrowser
from authentification import connect, fetch_token
from fastapi import FastAPI, Request
import uvicorn
from googleapiclient.discovery import build

from pydantic import BaseModel

class EventDateTime(BaseModel):
    dateTime: str
    timeZone: str

# === FastApi ====

class InterviewApp():
    def __init__(self):
        self.app = FastAPI()
        
    
    def calendar_service(self, service):
        self.service = service

interview = InterviewApp()        

#app = FastAPI()

# === OpenAI setup ===
client = OpenAI()
session = SQLiteSession("in-memory")


# === Utilities ===
def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def _summary_extractor(run_result: RunResult) -> str:
    """Extracts summary text from sub-agent results."""
    return str(run_result.final_output.summary)


# === Core Logic ===
async def plan_generator(
    cv_input, job_desc, name, role, goals,
    time_available, E_I, S_N, T_F, J_P, start_date, interview_date,
    google_calendar
):
    """Generates a personalized interview preparation plan."""
    system_prompt = f"""
    You are creating a personalized interview preparation plan for:
    - Name: {name}
    - Role: {role}
    - Goals: {goals}
    - Time available per day: {time_available} hours
    - Personality (Myers-Briggs):
        E/I: {E_I}, S/N: {S_N}, T/F: {T_F}, J/P: {J_P}
    Interview date: {interview_date} (starting {start_date})
    """

    job_prompt = f"\nJob Description:\n{job_desc}\n"
    base64_data = file_to_base64(cv_input.name)

    system_prompt += job_prompt

    # print("Step 1")
    # # === Step 1: Search plan extraction ===
    # plan = await Runner.run(
    #     planning_agent,
    #     [
    #         {"role": "assistant", "content": system_prompt + job_prompt},
    #         {"role": "user", "content": [{
    #             "type": "input_file",
    #             "file_data": f"data:application/pdf;base64,{base64_data}",
    #             "filename": cv_input.name,
    #         }]},
    #     ],
    # )
    # plan_extracted = plan.final_output_as(InterviewSearchPlan)

    # print("Step 2")
    # # === Step 2: CV Analysis ===
    # cv_info = await Runner.run(
    #     cv_job_reader,
    #     [
    #         {"role": "assistant", "content": system_prompt + job_prompt},
    #         {"role": "user", "content": [{
    #             "type": "input_file",
    #             "file_data": f"data:application/pdf;base64,{base64_data}",
    #             "filename": cv_input.name,
    #         }]},
    #     ],
    # )
    # cv_profile = cv_info.final_output_as(CandidateProfile)

    # print("Step 3")
    # # === Step 3: Research phase ===
    # search_results = await _perform_searches(plan_extracted)


    print("Step 4")
    # === Step 4: Compose final plan ===
    final_plan = await _write_plan(base64_data, system_prompt)
    print(_format_plan_for_ui(final_plan))
    return final_plan


async def _perform_searches(search_plan: InterviewSearchPlan) -> Sequence[str]:
    with custom_span("Search the web"):
        tasks = [asyncio.create_task(_search(item)) for item in search_plan.searches]
        results: list[str] = []
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                results.append(result)
        return results


async def _search(item: InterviewSearchItem) -> str | None:
    input_data = f"Search term: {item.query}\nReason: {item.reason}"
    try:
        result = await Runner.run(search_agent, input_data)
        return str(result.final_output)
    except Exception:
        return None


async def _write_plan(cv, system_prompt) -> CompletePlan:
    personality_tool = personality_judge_agent.as_tool(
        "personality_analysis", "Adapts plan based on personality", _summary_extractor
    )
    feasibility_tool = feasibility_agent.as_tool(
        "feasibility_analysis", "Adapts plan for realism", _summary_extractor
    )
    writer_with_tools = writer_agent.clone(tools=[personality_tool, feasibility_tool, create_event])
    result = await Runner.run(
        writer_with_tools,
        [
            {"role": "assistant", "content": system_prompt},
            {"role": "user", "content":[{
                "type": "input_file",
                "file_data": f"data:application/pdf;base64,{cv}",
                "filename": "CV"
            }]}
        ]
    )
    return result.final_output_as(CompletePlan)


def _format_plan_for_ui(final_plan: CompletePlan) -> str:
    """Formats CompletePlan into a structure suitable for Gradio UI."""
    lines = []
    lines.append("Final Plan Breakdown:\n")
    lines.append(f"Summary: {final_plan.short_summary}\n")
    
    for day_plan in final_plan.daily_plans:
        lines.append(f"Day {day_plan.day}")
        lines.append("-----")
        lines.append("tasks:")
        for task in day_plan.tasks:
            lines.append(f" - {task.name}")
            lines.append(f"   {task.description}")
        lines.append("")  # blank line between days

    return "\n".join(lines)


def run_generate_plan(*args):
    print("Run generate plan")
    google_calendar = args[12]
    if google_calendar:
        print("User wants to add events to calendar")
        print("We need to athenticate")
        #Retrieve correct url
        url = connect()
        webbrowser.open(url)
        
    result = asyncio.run(plan_generator(*args))
   # render_plan(result)
    print("Finished run ")
    return result

@interview.app.get("/oauth2callback/")
async def oauth2callback(request: Request) -> int:

    # response = requests.get("https://f21c5a511ed06cf0ea.gradio.live/oauth2callback", allow_redirects=False)
    # # The Location header contains the redirect URL with ?code=...
    # redirect_url = response.headers.get('Location')

    # if redirect_url:
    #     from urllib.parse import urlparse, parse_qs
    #     code = parse_qs(urlparse(redirect_url).query).get('code', [None])[0]
    #     print(code)
    #     return code
    # else:
    #     print("No redirect with code found.")
   
    print("callback oauth")
    print(request.url)
    credentials = fetch_token(str(request.url))
    print(credentials)

    service = build("calendar", "v3", credentials=credentials)

    interview.service = service

    
    return 1

@function_tool
def create_event(name: str, start: EventDateTime, end: EventDateTime):
    """
    Create a calendar event in the user's primary Google Calendar.

    Parameters
    ----------
    name : str
        The title or summary of the event.

    start : EventDateTime
        Must include:
        - "dateTime": ISO 8601 timestamp string (e.g., "2025-11-28T09:00:00-07:00")
        - "timeZone": IANA timezone string (e.g., "America/New_York")

    end : EventDateTime
        Must include:
        - "dateTime": ISO 8601 timestamp string
        - "timeZone": IANA timezone string

    Behavior
    --------
    This tool inserts a new event using the Google Calendar API into the
    user's primary calendar. The agent should call this function whenever it
    wants to schedule a meeting, reminder, interview session, or any other
    time-bound activity.
    """

    event = {
        "summary": name,
        "start": start.model_dump(mode='json'),
        "end": end.model_dump(mode='json')
    }
    interview.service.events().insert(calendarId='primary', body=event).execute()
    

# http://localhost:8080/oauth2callback?state=0eAatgddDRBlMxq8AKsQSJMdAxadbu&code=4/0Ab32j93MBnHsy9Qdc-rPKDWJEim52Btrcg1LY7V0mPC5TAGcOI5dPoOaQY5-tJfQjkBl1Q&scope=https://www.googleapis.com/auth/calendar.events.owned


# === Gradio UI ===
with gr.Blocks(title="Interview Preparation Suite") as demo:
    plan = gr.State(value=None)
    gr.Markdown(
        """
        # 🧭 Interview Preparation Assistant  
        Upload your CV and job description, then receive a **personalized roadmap** for interview preparation.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            cv_input = gr.File(label="📄 Upload CV (PDF or DOCX)")
            job_desc = gr.Textbox(label="Job Description", lines=10, placeholder="Paste job description here...")
            name = gr.Textbox(label="Full Name")
            role = gr.Textbox(label="Current Role / Field")
            goals = gr.Textbox(label="Career Goals", lines=2)
        with gr.Column(scale=1):
            time_available = gr.Slider(1, 10, value=2, step=1, label="Daily Study Hours")
            start_date = gr.Textbox(label="Start Date (YYYY-MM-DD)")
            interview_date = gr.Textbox(label="Interview Date (YYYY-MM-DD)")
            gr.Markdown("### 🧠 Myers–Briggs Personality")
            E_I = gr.Radio(["Extraversion (E)", "Introversion (I)"], label="Energy", value="Introversion (I)")
            S_N = gr.Radio(["Sensing (S)", "Intuition (N)"], label="Information", value="Intuition (N)")
            T_F = gr.Radio(["Thinking (T)", "Feeling (F)"], label="Decision", value="Thinking (T)")
            J_P = gr.Radio(["Judging (J)", "Perceiving (P)"], label="Lifestyle", value="Judging (J)")

    google_calendar = gr.Checkbox(label="Add tasks to google calendar")
    submit_btn = gr.Button("🚀 Generate Interview Plan", variant="primary")
    

    @gr.render(inputs=plan)
    def render_plan(plan: CompletePlan):
        print("Render plan", plan,type(plan))
        if not plan:
            print("None")
            gr.Markdown("### Plan Summary will appear here...")
            gr.Markdown("### No plan generated")
        else:
            summary_md = f"### 🗒️ Summary\n{plan.short_summary}"
            gr.Markdown(value=summary_md)
            print("Building accordion")
            # Build dynamic accordions
            with gr.Group() as accordion_group:
                for day_info in plan.daily_plans:
                    task_md = "\n".join([f"- **{t.name}**:\n {t.description}" for t in day_info.tasks])
                    with gr.Accordion(label=f"📅 Day {day_info.day}", open=False):
                        gr.Markdown(task_md)
       
        
    # First step: generate raw plan data
    submit_btn.click(
        fn=run_generate_plan,
        inputs=[cv_input, job_desc, name, role, goals, time_available, E_I, S_N, T_F, J_P, start_date, interview_date, google_calendar],
        outputs=[plan]
    )

   # gr.api(oauth2callback)

    ## Quand on pese sur run_generate_plan, je veux lancer d abord l authentification si elle a ete coche
    # Je dois trouver comment exactement lancer l authentification. Je crois que c est simplement de faire une requete specifique a l url
    # d authentification en utilisant mon client secret fourni par google et ensuite une reponse sera ecoute dans un endpoint de mon api

    # Dans ce endpoint, je defenierai une fonction qui devrai extraire le token pour ensuite utliser l api google au nom de lutilisateur
    # si il a accepte

    # Je dois avoir moins de texte, ca doit prendre moins de temps, je dois ajouter les taches au calendrier

    # Maintenant ljout dans le calendrier fonctionne, je peux utiliser un agent pour le faire



    

    # Second step: render formatted plan in the UI
#     plan_data.then(
#         fn=render_plan,
#         inputs=[plan_data],
#         outputs=[summary_box, accordion_group],
# )


if __name__ == "__main__":
    # app, _, _ = demo.launch(server_name="localhost", server_port=8080, share=True)
    # app.add_api_route("/oauth2callback", status_code=200)
   
    gr.mount_gradio_app(app=interview.app,blocks=demo,path="/gradio",server_name="localhost", server_port=8080)
    uvicorn.run(interview.app, host="localhost", port=8080)
