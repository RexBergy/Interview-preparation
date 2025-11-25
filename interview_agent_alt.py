from __future__ import annotations
import asyncio
import base64
from typing import Sequence
import gradio as gr

from openai import OpenAI
from agents import Agent, RunResult, Runner, function_tool, CodeInterpreterTool, SQLiteSession, custom_span
from local_agents.cv_plus_job import cv_job_reader, CandidateProfile
from local_agents.planner import planning_agent, InterviewSearchPlan, InterviewSearchItem
from local_agents.material_search import search_agent
from local_agents.writer import writer_agent, CompletePlan
from local_agents.progress_judge import feasibility_agent
from local_agents.personality_judge import personality_judge_agent
from pydantic import BaseModel

# === OpenAI setup ===
client = OpenAI()

async def _summary_extractor(run_result: RunResult) -> str:
    """Custom output extractor for sub-agents that return an AnalysisSummary."""
    return str(run_result.final_output.summary)


# === File handling ===
@function_tool
def upload_file(file_path: str):
    """Uploads a file and returns base64 content."""
    return file_to_base64(file_path)

def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")




session = SQLiteSession("in-memory")

# === Logic ===

async def plan_generator(cv_input, 
                         job_desc, 
                         name, 
                         role, 
                         goals, 
                         time_available, 
                         E_I, 
                         S_N, 
                         T_F, 
                         J_P, 
                         start_date, 
                         interview_date):
    """
    Generates a personalized interview preparation plan based on multiple factors
    """

    system_prompt = f"""
    You are creating a personalized interview preparation plan for a user with the following profile:
    - Name: {name}
    - Current Role/Field: {role}
    - Career Goals: {goals}
    - Time Availble per day: {time_available} hours
    - Personality Type Myers-Briggs:
        -  introversion/extraversion -> {E_I}
        -  sensing/intuition -> {S_N}
        -  thinking/feeling -> {T_F}
        -  judging/perceiving -> {J_P}

    Incorporate this information into the planning process.

    The interview is scheduled to take plac on {interview_date} starting from {start_date}
    """

    job_description_prompt = f"""
    Here is the job description for the target position:
    {job_desc}
    """

    base64_data = file_to_base64(cv_input.name)
    # Step 1: CV reader to extract strenghts and weaknesses
    plan = await Runner.run(
        planning_agent, 
        [
            {
                "role": "assistant",
                "content": system_prompt + " " + job_description_prompt
            },
            {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_data": f"data:application/pdf;base64,{base64_data}",
                            "filename": f"{cv_input.name}",
                        }
                    ],
                },
            ])
    plan_extracted = plan.final_output_as(InterviewSearchPlan)
    # print("Searches to be performed:")
    # for item in plan_extracted.searches:
    #     print("Reason: ",item.reason)
    #     print("Query: ", item.query)

   # print("CV Info Extracted:", plan_extracted)
    cv_info = await Runner.run(
        cv_job_reader, 
        [
            {
                "role": "assistant",
                "content": system_prompt + " " + job_description_prompt
            },
            {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_data": f"data:application/pdf;base64,{base64_data}",
                            "filename": f"{cv_input.name}",
                        }
                    ],
                },
            ])
    
    cv_info_extracted = cv_info.final_output_as(CandidateProfile)
    #print("CV Info Extracted:", cv_info_extracted)
    # for strenght in cv_info_extracted.strengths:
    #     print("Strength:", strenght)
    # for weakness in cv_info_extracted.weaknesses:
    #     print("Weakness:", weakness)

    # for tech_gap in cv_info_extracted.technical_skills_gap:
    #     print("Technical Skill Gap:", tech_gap)

    # for soft_gap in cv_info_extracted.soft_skills_gap:
    #     print("Soft Skill Gap:", soft_gap)

    # Step 2: Planner agent



    # await Runner.run(
    #     planning_agent,
    #     cv_info_extracted
    # )

    # Step 3: Search

    search_results = await _perform_searches(plan_extracted)

    # print("Search Results:")
    # print("--------------")
    # for result in search_results:
    #     print("Result: \n",result)
    #     print("------------\n")
    # Step 4: Judges (progress, personality, feasibility)

    # Step 5: Writer

    final_plan = await _write_plan(search_results, cv_info_extracted, system_prompt)

    #print("Final Plan:\n", final_plan)
    print("Final Plan Breakdown:\n")
    print("Summary", final_plan.short_summary)
    for day_plan in final_plan.daily_plans:
        print("Day", day_plan.day)
        
        print("-----")
        print("tasks:")
        for task in day_plan.tasks:
            print(" - ", task.name)
            print("  ", task.description)

   

    return format_final_plan(final_plan)

def format_final_plan(final_plan: CompletePlan) -> str:
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

async def _write_plan(search_results: Sequence[str], candidate_profile: CandidateProfile, candidate_info: str) -> CompletePlan:

    input_data = f"Search Results: {search_results}\nCandidate Profile: {candidate_profile}\nCandidate Info: {candidate_info}"

    personality_judge_tool = personality_judge_agent.as_tool(
            tool_name="personality_analysis",
            tool_description="Use to analyze and adapt the plan based on a personality type",
            custom_output_extractor=_summary_extractor,
        )
    feasibility_tool = feasibility_agent.as_tool(
        tool_name="feasibility_analysis",
        tool_description="Use to analyze and adapt the plan based on its feasibility",
        custom_output_extractor=_summary_extractor,
    )
    writer_with_tools = writer_agent.clone(tools=[personality_judge_tool, feasibility_tool])
    result = await Runner.run(writer_with_tools, input_data)
    return result.final_output_as(CompletePlan)

async def _perform_searches(search_plan: InterviewSearchPlan) -> Sequence[str]:
        with custom_span("Search the web"):
            tasks = [asyncio.create_task(_search(item)) for item in search_plan.searches]
            results: list[str] = []
            num_completed = 0
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    results.append(result)
                num_completed += 1
            return results
        
async def _search(item: InterviewSearchItem) -> str | None:
        input_data = f"Search term: {item.query}\nReason: {item.reason}"
        try:
            result = await Runner.run(search_agent, input_data)
            return str(result.final_output)
        except Exception:
            return None


def run_generate_plan(
        v_input, 
        job_desc, 
        name, 
        role, 
        goals, 
        time_available, 
        E_I, 
        S_N, 
        T_F, 
        J_P,
        start_date, 
        interview_date):
    
    return asyncio.run(plan_generator(
        v_input, 
        job_desc, 
        name, 
        role, 
        goals, 
        time_available, 
        E_I, 
        S_N, 
        T_F, 
        J_P,
        start_date, 
        interview_date))

# === Gradio Interface ===
with gr.Blocks(title="Interview Preparation Suite") as demo:
    gr.Markdown("## 🧭 Interview Preparation Assistant\nAn app to assess your personality and design a tailored interview roadmap.")

    with gr.Row():
        cv_input = gr.File(label="Upload your CV (PDF or DOCX)")
        job_desc = gr.Textbox(label="Job Description", lines=8, placeholder="Paste the job description here...")
        name = gr.Textbox(label="Full Name")
        role = gr.Textbox(label="Current Role or Field")
        goals = gr.Textbox(label="Career Goals", lines=2)
        time_available = gr.Slider(label="Hours per day available for study", minimum=1, maximum=10, step=1)
        start_date = gr.Textbox(label="Start Date")
        interview_date = gr.Textbox(label="Interview Date")

    gr.Markdown("### 🧩 Myers–Briggs Personality Dimensions")
    with gr.Row():
        E_I = gr.Radio(["Extraversion (E)", "Introversion (I)"], label="Energy Orientation", value="Introversion (I)")
        S_N = gr.Radio(["Sensing (S)", "Intuition (N)"], label="Information Processing", value="Intuition (N)")
        T_F = gr.Radio(["Thinking (T)", "Feeling (F)"], label="Decision Making", value="Thinking (T)")
        J_P = gr.Radio(["Judging (J)", "Perceiving (P)"], label="Lifestyle", value="Judging (J)")


    gr.Markdown("### 📅 Daily Plan Overview")
    day_boxes = []
    num_days = 14  # adjustable or computed dynamically later
    for i in range(1, num_days + 1):
        with gr.Accordion(f"Day {i}", open=False):
            box = gr.CheckboxGroup(label=f"Tasks for Day {i}", choices=[])
            day_boxes.append(box)
    submit_btn = gr.Button("Generate Interview Plan")
    output_box = gr.Textbox(label="Generated Plan", lines=30)

    submit_btn.click(
        fn=run_generate_plan,
        inputs=[cv_input, job_desc, name, role, goals, time_available, E_I, S_N, T_F, J_P, start_date, interview_date],
        outputs=output_box,
    )
    


# === Run Locally ===
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)


# Je dois mettre en place la recherche, ensuite les juges, puis /crire cela dans un plan separe en jours

"""
Searches to be performed:
Reason:  Understand AKS production readiness to speak about reliability, scaling, and ops tradeoffs
Query:  site:learn.microsoft.com Azure Kubernetes Service production best practices 2025
Reason:  Be able to justify architecture choices between services for different workloads
Query:  site:learn.microsoft.com Azure App Service vs Azure Kubernetes Service when to use 2025
Reason:  Close skill gap in Node/TypeScript/Express with production-grade patterns and validation
Query:  TypeScript Express REST API best practices 2025 OpenAPI validation zod class-validator
Reason:  Show strong testing practice on the Node side with coverage and E2E
Query:  site:jestjs.io ts-jest TypeScript Jest configuration with supertest guide 2025
Reason:  Instrument services for tracing/metrics to match monitoring expectations
Query:  site:opentelemetry.io Node.js Express instrumentation tracing metrics exporter Prometheus 2025
Reason:  Discuss cluster monitoring setup confidently for AKS
Query:  site:prometheus.io Kubernetes monitoring best practices AKS scrape config 2025
Reason:  Design efficient image/object storage and metadata patterns on Azure
Query:  site:learn.microsoft.com Azure Blob Storage best practices images metadata streaming 2025
Reason:  Model image and metadata efficiently for performance and scale
Query:  site:mongodb.com schema design images metadata time-series best practices 2025
Reason:  Use Redis effectively for caching, queues, and streams in Node services
Query:  site:redis.io caching patterns Node.js Redis Streams pub/sub best practices 2025
Reason:  Build small, secure containers for Python/C++ CV services
Query:  site:docs.docker.com multi-stage builds Python C++ OpenCV slim images 2025
Reason:  Speak to deploying CV microservices and GPU considerations on AKS
Query:  Deploy Python FastAPI OpenCV to AKS GPU node pool tutorial 2025
Reason:  Demonstrate CI/CD knowledge aligned to the stack (Azure DevOps/GitHub Actions)
Query:  site:learn.microsoft.com Azure DevOps or GitHub Actions YAML build test Node docker push ACR deploy to AKS 2025
Reason:  Show mastery of collaborative workflows required in the role
Query:  site:git-scm.com interactive rebase merge strategies code review best practices 2025
Reason:  Prepare for role-specific technical and scenario questions
Query:  Backend engineer interview questions 2025 Node.js TypeScript Express Azure AKS
Reason:  Confidently discuss performance validation and introduce load tests into CI
Query:  k6 load testing REST API tutorial GitHub Actions Azure DevOps 2025
"""

"""
Strength: Strong Python engineering background (100k+ LOC) with proven ability to build robust applications from scratch
Strength: Hands-on experience deploying and maintaining multiple apps for hundreds of users; exposure to production support and distributed environments
Strength: Demonstrated performance optimization and parallelization skills (reduced a 24h job to 15 minutes)
Strength: Quality focus: significantly increased unit test coverage; set up CI/CD quickly (TeamCity)
Strength: Agile team experience; effective cross-functional collaboration with engineers/analysts; delivered 20+ presentations to stakeholders
Strength: Clear ownership and product orientation (project business lead; 100% user satisfaction)
Strength: Documentation and developer enablement (onboarding web page)
Strength: Comfort handling large datasets and data analysis/visualization
Strength: Some C/C++ exposure and solid CS fundamentals from MSc/BSc; fast learner with initiative
Strength: Based in Montreal; aligns with location and partial-remote setup
Weakness: Does not meet the 5+ years backend experience requirement (≈3 years professional)
Weakness: No demonstrated Node.js/TypeScript/Express experience; REST API design experience not evidenced
Weakness: No evidence of Azure App Service, AKS, or Kubernetes; no Docker/containerization listed
Weakness: Database stack mismatch: no MongoDB/Redis experience; SQL only at a basic level and no schema design claims
Weakness: Testing stack gap for backend services (no Jest/Mocha; Pytest listed as basic; no clear E2E/integration test automation)
Weakness: Git workflows listed as basic, which conflicts with the requirement for expert branching/rebasing/review practices
Weakness: Linux proficiency listed as basic, which is weak for a backend/DevOps-heavy role
Weakness: C++ listed as basic; role expects good understanding (for CV services)
Weakness: No monitoring/observability experience (Prometheus, Grafana, OpenTelemetry) or load testing
Weakness: No explicit experience with computer vision, mobile (iOS/Android), or image streaming/storage concerns
Weakness: Cloud CI/CD tools mismatch (Azure DevOps/GitHub Actions not shown; TeamCity only)
Weakness: Security and production-readiness not evidenced (authn/authz, secrets management, OWASP, incident response/on-call)
Technical Skill Gap: Node.js/TypeScript/Express (designing and implementing RESTful APIs)
Technical Skill Gap: Azure App Service, Azure Kubernetes Service (AKS), Kubernetes fundamentals
Technical Skill Gap: Docker and container-based deployments
Technical Skill Gap: MongoDB and Redis (data modeling, performance, caching patterns)
Technical Skill Gap: Automated testing across layers (unit/integration/E2E) with Jest/Mocha; strengthening Pytest beyond basic
Technical Skill Gap: Git expertise (advanced branching models, rebases, code reviews, CI gating)
Technical Skill Gap: Linux proficiency for backend ops and container debugging
Technical Skill Gap: C++ proficiency to a working level for CV-related services
Technical Skill Gap: Monitoring/observability (Prometheus, Grafana, OpenTelemetry), logging/metrics/tracing
Technical Skill Gap: Load/performance testing and capacity planning
Technical Skill Gap: Cloud CI/CD with Azure DevOps or GitHub Actions; pipelines for Node/Python services
Technical Skill Gap: REST API standards and tooling (OpenAPI/Swagger, contract testing)
Technical Skill Gap: Security for backend services (OAuth2/OIDC, JWT, secrets, OWASP Top 10, secure coding)
Technical Skill Gap: Storage and streaming of images/metadata at scale (blob storage patterns, CDN, presigned URLs, multipart uploads)
Technical Skill Gap: Infrastructure as code/packaging for k8s (Helm, Kustomize), container registries
Soft Skill Gap: Operating in a startup pace with high autonomy and rapid iteration vs prior large enterprise context
Soft Skill Gap: Participating in and driving rigorous code review culture across multiple stacks (Node, Python, C++)
Soft Skill Gap: Coordinating closely with mobile and computer vision teams to deliver integrated features end-to-end
Soft Skill Gap: Handling production incidents/on-call and rapid diagnosis/resolution under pressure
Soft Skill Gap: Articulating trade-offs for cloud cost/performance/reliability and influencing sprint scope in Scrum ceremonies
Soft Skill Gap: Communicating API contracts and operational expectations clearly through concise technical documentation and RFCs
"""
