from __future__ import annotations

import asyncio
import os
import webbrowser
import time
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import List, Dict, Any, Tuple

import gradio as gr
from gradio.themes.base import Base
from fastapi import FastAPI, Request
from openai.types.responses import ResponseTextDeltaEvent

# When running locally, disable OAuthlib's HTTPs verification.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Import Local Agents & Modules
from agents import Runner
from local_agents.writer import writer_agent, CompletePlan, DailyPlan, Task
from calendar_utils import connect, smart_schedule_quests, oauth2callback, calendar_service
from game_logic import init_game_state, render_quest_board, calculate_player_stats
from quiz_engine import generate_quiz_for_task
from plan_parser import parse_markdown_to_plan

# === GLOBALS & SETUP ===
app = FastAPI()

# ============================================================
# ⚡ MODULE 4: GENERATION LOGIC (Global)
# ============================================================

async def stream_plan_generation(role, goal, job_description, hours, start_date_ts, interview_date_ts, use_cal, pref_time, progress=gr.Progress()):
    """Generates the plan, syncs to Calendar, and initializes Game."""
    
    # 1. Validation & Setup
    if not role or not goal:
        raise gr.Error("Please fill in Role and Goals.")
        
    try:
        # Check if Gradio sent a float timestamp or string
        if isinstance(start_date_ts, (int, float)):
             start_dt = datetime.fromtimestamp(start_date_ts)
        else:
             # Try parsing string if not timestamp
             start_dt = date_parser.parse(str(start_date_ts))
             
        if isinstance(interview_date_ts, (int, float)):
             interview_dt = datetime.fromtimestamp(interview_date_ts)
        else:
             interview_dt = date_parser.parse(str(interview_date_ts))
             
        days_avail = (interview_dt - start_dt).days
    except Exception as e:
        print(f"Date Error: {e}")
        days_avail = 7
        start_dt = datetime.now()

    # Auth Check
    if use_cal and not calendar_service:
        auth_url = connect()
        webbrowser.open(auth_url)
        max_wait = 60
        for i in range(max_wait):
            if calendar_service: break
            await asyncio.sleep(1)
            if i % 5 == 0: progress(0.2, desc=f"⏳ Waiting for Google Auth... ({60-i}s)")
        if not calendar_service: raise ValueError("Calendar auth failed.")
    
    # 2. Switch to View (Hide Step 1, Show Step 2)
    yield (
        "", gr.update(visible=False), gr.update(visible=True), 
        [], [], "", 
        gr.update(visible=True), gr.update(visible=False)
    )

    # 3. Prompt
    system_prompt = f"""
    CONTEXT:
    - Candidate Role: {role}
    - Goals: {goal}
    - Job Description: {job_description if job_description else "Not provided."}
    - Logistics: {days_avail} days available, {hours} hours/day.
    
    INSTRUCTIONS:
    Write a gamified preparation plan. Create quests specific to the role of {role}. 
    If a job description is provided, tailor the quests to the requirements and responsibilities listed. 
    The quests should cover both general skills for the role and specific points from the job description.
    Format carefully as requested.
    """

    # 4. Stream Agent
    full_response = ""
    result = Runner.run_streamed(writer_agent, system_prompt)

    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            full_response += event.data.delta
            yield (
                full_response, gr.update(), gr.update(),
                [], [], "",
                gr.update(), gr.update()
            )

    # 5. Initialize Game
    plan_obj = parse_markdown_to_plan(full_response)
    
    # 6. CALENDAR SYNC
    if use_cal:
        progress(0.8, desc="📅 Syncing Quests to Calendar...")
        await smart_schedule_quests(plan_obj, start_dt, int(pref_time))
    
    game_tasks = init_game_state(plan_obj)
    board_df = render_quest_board(game_tasks)
    board_samples = board_df.values.tolist()
    
    xp, lvl, title, xp_in_level, xp_per_level = calculate_player_stats(game_tasks)
    progress_percent = (xp_in_level / xp_per_level) * 100
    stats_html = f"""
    <div style='text-align:center; padding:10px; background:#292524; border-radius:8px; border: 1px solid #44403c;'>
        <h2>Level {lvl} {title}</h2>
        <div style='width: 100%; background-color: #44403c; border-radius: 5px; margin-bottom: 5px; overflow: hidden;'>
            <div style='width: {progress_percent}%; height: 24px; background-color: #b0b0b0; border-radius: 5px; text-align: center; color: #000000; line-height: 24px; transition: width 0.5s ease-in-out;
                         background-image: linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent);
                         background-size: 40px 40px; animation: progress-bar-stripes 2s linear infinite;'>
                {xp_in_level} / {xp_per_level} XP
            </div>
        </div>
        <p style='margin:0;'>Total XP: ✨ {xp}</p>
    </div>
    """

    yield (
        "", gr.update(), gr.update(),
        game_tasks, gr.update(samples=board_samples), stats_html,
        gr.update(visible=False), gr.update(visible=True) # Hide loading, Show Board
    )


# ============================================================
# 🖥️ UI LAYOUT
# ============================================================

class MedievalFantasy(Base):
    def __init__(self):
        super().__init__(
            primary_hue=gr.themes.colors.slate, # Black/dark gray base
            secondary_hue=gr.themes.colors.gray, # Silver/light gray accents
            neutral_hue=gr.themes.colors.gray,
            font=(
                gr.themes.GoogleFont("Lora"),
                "ui-serif",
                "Georgia",
                "serif",
            ),
        )
        self.set(
            # Colors -- Black & Silver Theme
            body_background_fill="#0d0d0d",
            body_background_fill_dark="#0d0d0d",
            body_text_color="#e0e0e0", # Light silver text
            body_text_color_dark="#e0e0e0",

            button_primary_background_fill="#b0b0b0", # Silver
            button_primary_background_fill_dark="#b0b0b0",
            button_primary_text_color="#000000", # Black text on silver button
            
            button_secondary_background_fill="#333333", # Dark silver/charcoal
            button_secondary_background_fill_dark="#333333",
            button_secondary_text_color="#e0e0e0", # Light silver text

            # Component Styling
            block_background_fill="#1a1a1a", # Near-black
            block_border_width="1px",
            block_border_color="#333333", # Dark silver border
            block_title_text_color="#e0e0e0",

            input_background_fill="#333333",
            input_border_color="#555555",
            
            # Slider
            slider_color="#b0b0b0", # Silver
            slider_color_dark="#b0b0b0",
        )
css = """
.container { max-width: 900px; margin: auto; } 
.feedback { font-weight: bold; font-size: 1.1em; }
@keyframes progress-bar-stripes {
  from { background-position: 40px 0; }
  to { background-position: 0 0; }
}
"""

with gr.Blocks(title="Career Quest", theme=MedievalFantasy(), css=css) as demo:
    
    # Global State
    game_state_store = gr.State([]) 
    active_task_idx = gr.State(-1)
    active_quiz_data = gr.State([])

    gr.Markdown("# Career Quest: Gamified Prep", elem_classes="text-center")

    # --- STEP 1: SETUP ---
    with gr.Column(visible=True) as step_1_col:
        gr.Markdown("### 👤 Character Setup")
        with gr.Row():
            role_input = gr.Textbox(label="Target Role (Class)", placeholder="e.g. Nurse, Python Dev")
            hours_input = gr.Slider(1, 10, value=2, label="Hours per Day")
        
        goal_input = gr.Textbox(label="Main Quest Goal", placeholder="e.g. Land a senior role")
        job_description_input = gr.Textbox(label="Job Description (Optional)", placeholder="Paste the job description here to tailor your quests.")
        
        with gr.Row():
            start_date = gr.DateTime(label="Start Date")
            interview_date = gr.DateTime(label="Boss Battle Date")

        with gr.Row():
            use_cal = gr.Checkbox(label="📅 Sync Quests to Google Calendar")
            pref_time = gr.Dropdown(choices=[("Morning (9AM)", 9), ("Afternoon (2PM)", 14), ("Evening (6PM)", 18)], value=18, label="Quest Time")

        generate_btn = gr.Button("⚔️ Generate Campaign", variant="primary")

    # --- STEP 2: GAME BOARD ---
    with gr.Column(visible=False) as step_2_col:
        loading_msg = gr.Markdown("### 🧙‍♂️ The Oracle is crafting your destiny...", visible=False)
        raw_stream_output = gr.Markdown(visible=False)

        # Container for the main board (Hidden when quiz is open)
        with gr.Group(visible=False) as board_container:
            stats_display = gr.HTML()
            gr.Markdown("### 📜 Quest Board")
            
            with gr.Column(visible=True) as quest_board_col:
                quest_board = gr.Dataset(
                    components=["textbox", "textbox", "textbox", "textbox"],
                    headers=["Status", "Timeline", "Quest Objective", "Rewards"],
                )
                board_feedback = gr.Textbox(label="System Log", interactive=False)

            with gr.Column(visible=False) as quest_details_col:
                gr.Markdown("### ⚔️ Quest Details")
                quest_details_md = gr.Markdown("No quest selected.")
                with gr.Row():
                    start_quiz_btn = gr.Button("🧠 Start Quiz", variant="primary")
                    get_help_btn = gr.Button("📚 Get Help")
                back_to_board_btn = gr.Button("⬅️ Back to Quest Board")


        # Container for the Quiz Overlay (Hidden by default)
        with gr.Group(visible=False) as quiz_modal:
            gr.Markdown("## 🧠 Knowledge Check")
            q_header = gr.Markdown("Loading...")
            quiz_loading_msg = gr.Markdown("### 🧙‍♂️ Forging your questions...", visible=False)
            with gr.Group(visible=True) as quiz_questions_group:
                q1_comp = gr.Radio(label="Q1")
                q2_comp = gr.Radio(label="Q2")
                q3_comp = gr.Radio(label="Q3")
                q4_comp = gr.Radio(label="Q4", visible=False)
                q5_comp = gr.Radio(label="Q5", visible=False)
                q6_comp = gr.Radio(label="Q6", visible=False)
                submit_quiz_btn = gr.Button("Submit Answers", variant="primary")
            feedback_box = gr.Markdown(elem_classes="feedback")

    # ============================================================
    # 🔗 EVENT HANDLERS (DEFINED INSIDE BLOCKS FOR SCOPE)
    # ============================================================

    def on_quest_click(evt: gr.SelectData, game_tasks):
        """Handles clicking a Quest on the board."""
        if evt is None or not game_tasks:
            return {board_feedback: "⚠️ No task selected"}
        
        row_idx = evt.index
        if row_idx >= len(game_tasks):
            return {board_feedback: "⚠️ Error: Invalid Task Selection"}

        task = game_tasks[row_idx]
        
        if task['status'] == "🔒 LOCKED":
            return {
                board_feedback: "🚫 Quest Locked! Complete previous quests first.",
                quest_board_col: gr.update(visible=True),
                quest_details_col: gr.update(visible=False)
            }
        
        if task['status'] == "COMPLETED":
            return {
                board_feedback: "✅ Quest already completed!",
                quest_board_col: gr.update(visible=True),
                quest_details_col: gr.update(visible=False)
            }

        details_md = f"""
        **Quest:** {task['name']}
        **Description:** {task['desc']}
        **Difficulty:** {task['difficulty']}
        **XP:** {task['xp_reward']}
        """
        return {
            quest_board_col: gr.update(visible=False),
            quest_details_col: gr.update(visible=True),
            quest_details_md: gr.update(value=details_md),
            active_task_idx: row_idx,
            board_feedback: ""
        }

    def start_quiz(row_idx, game_tasks, role):
        """Generates and displays the quiz for the active task."""
        if row_idx == -1 or not game_tasks:
            raise gr.Error("No active quest selected.")

        # Show loading state
        yield {
            quest_details_col: gr.update(visible=False),
            quiz_modal: gr.update(visible=True),
            quiz_loading_msg: gr.update(visible=True),
            quiz_questions_group: gr.update(visible=False),
            feedback_box: ""
        }
        
        task = game_tasks[row_idx]
        
        quiz_questions = generate_quiz_for_task(role, task['name'], task['desc'], task['difficulty'])
        num_questions = len(quiz_questions)

        updates = {
            quiz_loading_msg: gr.update(visible=False),
            quiz_questions_group: gr.update(visible=True),
            active_quiz_data: quiz_questions,
            q_header: gr.update(value=f"### ⚔️ Quest: {task['name']}")
        }
        
        all_q_comps = [q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp]
        for i, q_comp in enumerate(all_q_comps):
            if i < num_questions:
                updates[q_comp] = gr.update(
                    label=quiz_questions[i]['q'],
                    choices=quiz_questions[i]['options'],
                    value=None,
                    visible=True
                )
            else:
                updates[q_comp] = gr.update(visible=False, value=None)
        
        yield updates

    def get_help(row_idx, game_tasks):
        """Displays help information for the selected quest."""
        if row_idx == -1 or not game_tasks:
             return {quest_details_md: "Could not find help for this quest."}
        task = game_tasks[row_idx]
        
        # In a real scenario, you might call another agent or search a vector DB.
        # For now, we'll generate some placeholder links.
        help_md = f"""
        **Quest:** {task['name']}
        
        **Description:** {task['desc']}
        
        Here are some resources that might help you:
        
        *   [How to learn about {task['name']}](https://www.google.com/search?q=How+to+learn+about+{task['name'].replace(' ', '+')})
        *   [A video explaining {task['name']}](https://www.youtube.com/results?search_query={task['name'].replace(' ', '+')})
        *   [Related articles on the topic](https://en.wikipedia.org/w/index.php?search={task['name'].replace(' ', '+')})
        """
        return {quest_details_md: help_md}
        
    def back_to_board():
        return {
            quest_board_col: gr.update(visible=True),
            quest_details_col: gr.update(visible=False),
            quiz_modal: gr.update(visible=False)
        }

    def submit_quiz_answers(idx, a1, a2, a3, a4, a5, a6, quiz_data, game_tasks):
        if idx == -1 or not game_tasks:
            return {feedback_box: "⚠️ Error: No active quest."}

        num_questions = len(quiz_data)
        user_answers = [a1, a2, a3, a4, a5, a6][:num_questions]
        
        score = 0
        for i, question in enumerate(quiz_data):
            correct_string = question['options'][question['correct_index']]
            if user_answers[i] and user_answers[i].strip() == correct_string.strip():
                score += 1

        pass_threshold = -(-num_questions * 2 // 3)  # Ceiling division
        if score < pass_threshold:
            return {
                feedback_box: f"❌ {score}/{num_questions} Correct. You need {pass_threshold} to pass. Try again!",
            }
        
        game_tasks[idx]['status'] = "COMPLETED"
        if idx + 1 < len(game_tasks):
            game_tasks[idx + 1]['status'] = "🔓 UNLOCKED"
            
        xp, lvl, title, xp_in_level, xp_per_level = calculate_player_stats(game_tasks)
        progress_percent = (xp_in_level / xp_per_level) * 100 if xp_per_level > 0 else 0
        new_stats = f"""
        <div style='text-align:center; padding:10px; background:#2a2a2a; border-radius:8px; border: 1px solid #b0b0b0;'>
            <h2>Level {lvl} {title}</h2>
            <div style='width: 100%; background-color: #44403c; border-radius: 5px; margin-bottom: 5px; overflow: hidden;'>
                <div style='width: {progress_percent}%; height: 24px; background-color: #b0b0b0; border-radius: 5px; text-align: center; color: #000000; line-height: 24px; transition: width 0.5s ease-in-out;
                             background-image: linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent);
                             background-size: 40px 40px; animation: progress-bar-stripes 2s linear infinite;'>
                    {xp_in_level} / {xp_per_level} XP
                </div>
            </div>
            <p style='margin:0;'>Total XP: ✨ {xp}</p>
        </div>
        """
        new_df = render_quest_board(game_tasks)
        new_samples = new_df.values.tolist()
        
        return {
            feedback_box: "🎉 Victory! Next Quest Unlocked.",
            quest_board_col: gr.update(visible=True),
            quest_details_col: gr.update(visible=False),
            quiz_modal: gr.update(visible=False),
            game_state_store: game_tasks,
            quest_board: gr.update(samples=new_samples),
            stats_display: gr.update(value=new_stats),
            board_feedback: "✅ Quest Complete!"
        }

    # --- WIRING ---
    generate_btn.click(
        fn=stream_plan_generation,
        inputs=[role_input, goal_input, job_description_input, hours_input, start_date, interview_date, use_cal, pref_time],
        outputs=[raw_stream_output, step_1_col, step_2_col, game_state_store, quest_board, stats_display, loading_msg, board_container]
    )

    quest_board.select(
        fn=on_quest_click,
        inputs=[game_state_store],
        outputs=[quest_board_col, quest_details_col, quest_details_md, active_task_idx, board_feedback]
    )
    
    start_quiz_btn.click(
        fn=start_quiz,
        inputs=[active_task_idx, game_state_store, role_input],
        outputs=[
            quest_details_col, quiz_modal, active_quiz_data, q_header, feedback_box, 
            q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp,
            quiz_loading_msg, quiz_questions_group
        ]
    )

    get_help_btn.click(
        fn=get_help,
        inputs=[active_task_idx, game_state_store],
        outputs=[quest_details_md]
    )

    back_to_board_btn.click(
        fn=back_to_board,
        inputs=[],
        outputs=[quest_board_col, quest_details_col, quiz_modal]
    )

    submit_quiz_btn.click(
        fn=submit_quiz_answers,
        inputs=[active_task_idx, q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp, active_quiz_data, game_state_store],
        outputs=[feedback_box, quest_board_col, quest_details_col, quiz_modal, game_state_store, quest_board, stats_display, board_feedback]
    )

if __name__ == "__main__":
    gr.mount_gradio_app(app, demo, path="/")
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)