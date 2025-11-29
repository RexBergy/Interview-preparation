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
from backend.local_agents.writer import writer_agent
from backend.calendar_utils import connect, smart_schedule_quests, oauth2callback, calendar_service
from backend.game_logic import init_game_state, render_quest_board, calculate_player_stats
from backend.quiz_engine import generate_quiz_for_task
from backend.plan_parser import parse_markdown_to_plan

# === GLOBALS & SETUP ===
app = FastAPI()

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="frontend"), name="static")

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
        <p style='margin: 5px 0;'>Lives: ❤️❤️❤️</p>
        <p style='margin:0;'>Total XP: ✨ {xp}</p>
    </div>
    """

    yield (
        "", gr.update(), gr.update(),
        game_tasks, gr.update(samples=board_samples), stats_html,
        gr.update(visible=False), gr.update(visible=True) # Hide loading, Show Board
    )


# ============================================================
# 🔗 EVENT HANDLERS (DEFINED INSIDE BLOCKS FOR SCOPE)
# ============================================================

def on_quest_click(evt: gr.SelectData, game_tasks, quest_failed):
    """Handles clicking a Quest on the board."""
    if evt is None or not game_tasks:
        return [gr.update(), gr.update(), gr.update(), -1, "⚠️ No task selected", False]
    
    row_idx = evt.index
    if row_idx >= len(game_tasks):
        return [gr.update(), gr.update(), gr.update(), -1, "⚠️ Error: Invalid Task Selection", False]

    task = game_tasks[row_idx]
    
    if task['status'] == "🔒 LOCKED":
        return [gr.update(visible=True), gr.update(visible=False), gr.update(), -1, "🚫 Quest Locked! Complete previous quests first.", False]
    
    if task['status'] == "COMPLETED":
        return [gr.update(visible=True), gr.update(visible=False), gr.update(), -1, "✅ Quest already completed!", False]

    details_md = f"""
    **Quest:** {task['name']}
    **Description:** {task['desc']}
    **Difficulty:** {task['difficulty']}
    **XP:** {task['xp_reward']}
    """
    return [gr.update(visible=False), gr.update(visible=True), details_md, row_idx, "", False]

def start_quiz(row_idx, game_tasks, role):
    """Generates and displays the quiz for the active task."""
    if row_idx == -1 or not game_tasks:
        raise gr.Error("No active quest selected.")

    # Reset lives and quest failed status
    player_lives = 3
    quest_failed = False

    # Show loading state
    yield [
        gr.update(visible=False), gr.update(visible=True), [], gr.update(), "",
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        gr.update(visible=True), gr.update(visible=False), player_lives, quest_failed
    ]
    
    task = game_tasks[row_idx]
    
    quiz_questions = generate_quiz_for_task(role, task['name'], task['desc'], task['difficulty'])
    num_questions = len(quiz_questions)

    # [quest_details_col, quiz_modal, active_quiz_data, q_header, feedback_box, q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp, quiz_loading_msg, quiz_questions_group, player_lives, quest_failed]
    updates = [
        gr.update(), gr.update(), quiz_questions, f"### ⚔️ Quest: {task['name']}", gr.update(),
    ]
    
    # This is a bit of a hack, since we don't have direct access to the UI components.
    # We yield a list of updates, and the UI file will have to apply them.
    # The UI file will know which component corresponds to which index.
    
    # We will send 6 updates for the quiz questions
    for i in range(6):
        if i < num_questions:
            updates.append(gr.update(
                label=quiz_questions[i]['q'],
                choices=quiz_questions[i]['options'],
                value=None,
                visible=True
            ))
        else:
            updates.append(gr.update(visible=False, value=None))
    
    updates.extend([gr.update(visible=False), gr.update(visible=True), player_lives, quest_failed])
    yield updates

def get_help(row_idx, game_tasks):
    """Displays help information for the selected quest."""
    if row_idx == -1 or not game_tasks:
         return ["Could not find help for this quest."]
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
    return [help_md]
    
def back_to_board():
    return [gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)]

def submit_quiz_answers(idx, a1, a2, a3, a4, a5, a6, quiz_data, game_tasks, player_lives):
    if idx == -1 or not game_tasks:
        return ["⚠️ Error: No active quest.", gr.update(), gr.update(), gr.update(), game_tasks, gr.update(), gr.update(), "", player_lives, False]

    num_questions = len(quiz_data)
    user_answers = [a1, a2, a3, a4, a5, a6][:num_questions]
    
    score = 0
    answers_feedback = "### Correct Answers:\n"
    for i, question in enumerate(quiz_data):
        correct_string = question['options'][question['correct_index']]
        user_answer = user_answers[i].strip() if user_answers[i] else ""
        correct_answer_text = f"- **Q{i+1}:** {correct_string}\n"
        answers_feedback += correct_answer_text
        if user_answer == correct_string.strip():
            score += 1

    pass_threshold = -(-num_questions * 2 // 3)  # Ceiling division
    
    if score < pass_threshold:
        player_lives -= 1
        
        # Recalculate stats to update lives display
        xp, lvl, title, xp_in_level, xp_per_level = calculate_player_stats(game_tasks)
        progress_percent = (xp_in_level / xp_per_level) * 100 if xp_per_level > 0 else 0
        lives_display = "❤️" * player_lives
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
            <p style='margin: 5px 0;'>Lives: {lives_display if player_lives > 0 else "💀"}</p>
            <p style='margin:0;'>Total XP: ✨ {xp}</p>
        </div>
        """

        if player_lives <= 0:
            # Game Over
            feedback_message = f"### 💔 Game Over 💔\n\n**Score:** {score}/{num_questions}\n\nYou have run out of lives. The quest will now reset with a new quiz.\n\n{answers_feedback}"
            return [feedback_message, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), game_tasks, gr.update(), new_stats, "Quest failed! Returning to board.", 3, True]
        else:
            # Try Again
            lives_left = "❤️" * player_lives
            feedback_message = f"### Incorrect\n\n**Score:** {score}/{num_questions} (Needed: {pass_threshold})\n\n{answers_feedback}\n\nYou have {lives_left} left. Try again!"
            return [feedback_message, gr.update(), gr.update(), gr.update(), game_tasks, gr.update(), new_stats, gr.update(), player_lives, False]

    # --- Correct ---
    game_tasks[idx]['status'] = "COMPLETED"
    if idx + 1 < len(game_tasks):
        game_tasks[idx + 1]['status'] = "🔓 UNLOCKED"
        
    xp, lvl, title, xp_in_level, xp_per_level = calculate_player_stats(game_tasks)
    progress_percent = (xp_in_level / xp_per_level) * 100 if xp_per_level > 0 else 0
    lives_display = "❤️" * player_lives
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
            <p style='margin: 5px 0;'>Lives: {lives_display}</p>
            <p style='margin:0;'>Total XP: ✨ {xp}</p>
        </div>
        """
    new_df = render_quest_board(game_tasks)
    new_samples = new_df.values.tolist()
    
    success_message = f"### 🎉 Victory! Quest Complete! 🎉\n\n**Score:** {score}/{num_questions}\n\n{answers_feedback}"

    return [success_message, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), game_tasks, gr.update(samples=new_samples), new_stats, "✅ Quest Complete! Next quest unlocked.", player_lives, False]
