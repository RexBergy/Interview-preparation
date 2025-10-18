import asyncio
import base64
import gradio as gr
from openai import OpenAI
from agents import Agent, ModelSettings, Runner, WebSearchTool, function_tool, CodeInterpreterTool, SQLiteSession

# Initialize OpenAI client and container
client = OpenAI()
container = client.containers.create(name="interview-agent-container")
code_interpreter = CodeInterpreterTool(tool_config={"type": "code_interpreter", "container": container.id})

# ===== File Handling Tool =====
@function_tool
def upload_file(file_path: str):
    """Uploads a file to the OpenAI servers and returns its base64 content."""
    return file_to_base64(file_path)

def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ===== Agent Setup =====
# ===== Instructions ====
planning_agent_instructions = """
# Role and Objective
You are an expert interview planning agent. Your task is to elaborate a roadmap for a user to prepare for a technical interview.

# Instructions
1. Read and understand the user's CV. Make sure it is uploaded and accessible.
2. Read and understand the job description provided by the user.
3. Find weaknesses in the user's profile compared to the job description.
4. Create a detailed daily plan to prepare for the interview.
5. Suggest resources (books, courses, articles, videos) for each topic in the plan.
6. The plan should be realistic and achievable.

# Output
"""

planning_agent = Agent(
    name="Interview Planning Agent",
    model="gpt-5-nano",
    instructions=planning_agent_instructions,
    tools=[upload_file, WebSearchTool(), code_interpreter],
)

progress_judge_agent = Agent(
    name="Progress Judge Agent",
    model="gpt-5-nano"
)

session = SQLiteSession("in-memory")

# ===== Async Logic =====
async def chat_with_agent(user_message, file_obj, job_description, chat_history):
    # Upload CV if provided
    if file_obj is not None:
        base64_data = file_to_base64(file_obj.name)
        #await Runner.run(planning_agent, f"User uploaded a CV: {base64_data[:100]}...", session=session)
        await Runner.run(
            planning_agent,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_data": f"data:application/pdf;base64,{base64_data}",
                            "filename": f"{file_obj.name}",
                        }
                    ],
                },
            ],
        )
    
    # Process job description
    if job_description:
        await Runner.run(planning_agent, f"Job description provided:\n{job_description}", session=session)

    # Run main chat turn
    result = await Runner.run(planning_agent, user_message, session=session)
    bot_reply = result.final_output
    chat_history.append((user_message, bot_reply))
    return "", chat_history

# ===== Gradio UI =====
with gr.Blocks(title="Interview Preparation Agent") as demo:
    gr.Markdown("## 🧠 Interview Preparation Agent\nYour AI assistant to plan and prepare for technical interviews.")

    with gr.Row():
        with gr.Column(scale=1):
            cv_upload = gr.File(label="Upload your CV (PDF or TXT)")
            job_desc = gr.Textbox(label="Paste job description", lines=5, placeholder="Paste job description here...")
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Conversation")
            user_input = gr.Textbox(label="Your message", placeholder="Ask a question or type 'start' to begin...")

    send_btn = gr.Button("Send")

    def sync_chat(user_msg, cv, job, hist):
        return asyncio.run(chat_with_agent(user_msg, cv, job, hist))

    send_btn.click(
        fn=sync_chat,
        inputs=[user_input, cv_upload, job_desc, chatbot],
        outputs=[user_input, chatbot],
    )

# ===== Run Locally =====
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
