import asyncio
import base64
import gradio as gr
from openai import OpenAI
from local_agents import Agent, Runner, WebSearchTool, function_tool, CodeInterpreterTool, SQLiteSession, ModelSettings
from .local_agents.cv_plus_job import cv_job_reader
from pydantic import BaseModel

# === OpenAI setup ===
client = OpenAI()
container = client.containers.create(name="interview-agent-container")
code_interpreter = CodeInterpreterTool(tool_config={"type": "code_interpreter", "container": container.id})

class DayPlan(BaseModel):
    day: int
    tasks: list[str]

class CompletePlan(BaseModel):
    plan: list[DayPlan]


# === File handling ===
@function_tool
def upload_file(file_path: str):
    """Uploads a file and returns base64 content."""
    return file_to_base64(file_path)

def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# === Agent Instructions ===
planning_agent_instructions = """
# Role and Objective
You are an expert interview planning agent. Your task is to elaborate a roadmap for a user to prepare for a technical interview.

# Instructions
1. Read and understand the user's CV.
2. Read and understand the job description.
3. Find weaknesses in the user's profile compared to the job description.
4. Create a daily plan to prepare for the interview.
5. Suggest resources and exercises.
6. Make the plan realistic and achievable.

# Output
A high-level preparation plan.
"""

progress_judge_agent_instructions = """
# Role
You are an expert judge on learning progression.

# Instructions
1. Read a learning plan and check its coherence.
2. Reorder or improve it to follow the right sequence.
3. Ensure the fundamentals come first.

# Output
A corrected, logical plan.
"""

personality_judge_agent_instructions = """
# Role
You are a personality fit judge.
You check if the proposed plan aligns with the personality type.

# Instructions
1. Analyze the proposed plan.
2. Compare it to the user's personality preferences based on the 4 Myers-Briggs dimensions:
   - Extraversion vs Introversion
   - Sensing vs Intuition
   - Thinking vs Feeling
   - Judging vs Perceiving
3. Adjust the plan to better suit the personality (for example, structured vs flexible learning, social vs solo activities).
4. Preserve the skill goals but adapt the method and pacing.

# Output
A corrected and personality-aligned plan.
"""

feasibility_agent_instructions = """
# Role
You are a feasibility analyst agent.
You evaluate if the proposed interview preparation plan is realistic, achievable, and well-balanced based on the user's constraints.

# Instructions
1. Review the proposed preparation plan in detail.
2. Consider the user's time availability, energy levels, and daily responsibilities (if provided).
3. Check whether the pacing, duration, and difficulty of the tasks are realistic.
4. Identify parts of the plan that might be too ambitious, unclear, or inefficient.
5. Suggest modifications to improve feasibility while preserving learning effectiveness.
6. Maintain a positive, encouraging tone while explaining adjustments.

# Output
Provide a revised plan that is achievable, efficient, and sustainable.
"""

material_fetcher_agent_instructions = """
# Role
You are a resource and material fetcher agent.
Your task is to enhance the interview preparation plan by finding relevant learning materials and practice resources.

# Instructions
1. Read the user's preparation plan and identify all mentioned skills, topics, and exercises.
2. For each skill or topic, suggest:
   - One or two high-quality free resources (videos, tutorials, documentation, blogs, articles).
   - Optionally, one paid or premium course/book if it is widely recognized.
3. Ensure all resources are practical, reliable, and accessible online.
4. If the plan already includes resources, evaluate their quality and replace or supplement them when necessary.
5. Keep the formatting clean and structured, organized by day or skill topic.

# Output
A detailed, resource-enriched version of the plan, ready for the user to follow.
"""

# === Agent Creation ===
planning_agent = Agent(
    name="Interview Planning Agent",
    model="gpt-5",
    instructions=planning_agent_instructions,
    model_settings=ModelSettings(verbosity="high")
    
  #  output_type=CompletePlan
)
output_agent = Agent(
    name="Output Agent",
    model="gpt-5-nano",
    instructions="You are an agent that formats the final output.",
    output_type=CompletePlan
)
progress_judge_agent = Agent(
    name="Progress Judge Agent",
    model="gpt-5-nano",
    instructions=progress_judge_agent_instructions,
)

personality_judge_agent = Agent(
    name="Personality Judge Agent",
    model="gpt-5-nano",
    instructions=personality_judge_agent_instructions,
)


feasibility_agent = Agent(
    name="Feasibility Agent",
    model="gpt-5-nano",
    instructions=feasibility_agent_instructions,
)


material_fetcher_agent = Agent(
    name="Material Fetcher Agent",
    model="gpt-5-nano",
    instructions=material_fetcher_agent_instructions,
    tools=[WebSearchTool()],
)



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
    # Step 1: Initial Plan
    initial_plan_result = await Runner.run(
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
    initial_plan = initial_plan_result.final_output

    # Step 2: Material Fetching
    material_fetching_result = await Runner.run(material_fetcher_agent, initial_plan, session=session)
    material_fetching = material_fetching_result.final_output

    # Step 3: Progress Judgement
    progress_judge_result = await Runner.run(progress_judge_agent, material_fetching, session=session)
    progress_judge = progress_judge_result.final_output

    # Step 4: Feasibility Analysis
    feasibility_result = await Runner.run(feasibility_agent, progress_judge, session=session)
    feasibility = feasibility_result.final_output
    
    # Step 5: Personality Alignment
    personality_judge_result = await Runner.run(personality_judge_agent, feasibility, session=session)
    final_plan = personality_judge_result.final_output

    #Step 6: Final Output Formatting
    final_output_result = await Runner.run(output_agent, final_plan, session=session)

    print("Final Plan Generated")
    print(final_output_result.final_output)

    return final_plan

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
