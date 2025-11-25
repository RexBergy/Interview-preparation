from __future__ import annotations

import asyncio
import json
import random
import re
import webbrowser
import time
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import List, Dict, Any, Tuple

import gradio as gr
from fastapi import FastAPI, Request
from googleapiclient.discovery import build
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent

# Import Local Agents
# (Assumes agents.py and local_agents/writer.py exist in your directory)
from agents import Runner
from local_agents.writer import writer_agent, CompletePlan, DailyPlan, Task
from authentification import connect, fetch_token

# === GLOBALS & SETUP ===
app = FastAPI()
client = OpenAI() # Main client for Quiz Generation
calendar_service = None 

# ============================================================
# 📅 MODULE 0: CALENDAR & AUTHENTICATION
# ============================================================

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

async def smart_schedule_quests(plan: CompletePlan, start_date: datetime, preferred_hour: int, progress=gr.Progress()):
    """
    Scans the user's real calendar for free slots and schedules the Quests.
    """
    if not calendar_service:
        return "❌ Calendar not authenticated."

    # 1. Setup Time Boundaries
    try:
        cursor = start_date.astimezone()
    except:
        cursor = start_date # Fallback if timezone issues

    # Align to preferred hour
    if cursor.hour < preferred_hour:
        cursor = cursor.replace(hour=preferred_hour, minute=0, second=0)

    # Fetch busy slots (Batch)
    end_horizon = cursor + timedelta(days=len(plan.daily_plans) + 5)
    
    try:
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=cursor.isoformat(), 
            timeMax=end_horizon.isoformat(), 
            singleEvents=True, 
            orderBy='startTime'
        ).execute()
    except Exception as e:
        print(f"Failed to list calendar events: {e}")
        return f"⚠️ Error fetching calendar: {e}"
    
    busy_slots = []
    for e in events_result.get('items', []):
        if 'start' in e and 'dateTime' in e['start']:
            busy_slots.append((
                date_parser.parse(e['start']['dateTime']),
                date_parser.parse(e['end']['dateTime'])
            ))

    # 2. Schedule Quests
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
            attempts = 0
            while not scheduled and attempts < 50: # Safety break
                attempts += 1
                proposed_end = cursor + timedelta(minutes=task.duration)
                
                # Check Overlaps
                conflict = False
                for (b_start, b_end) in busy_slots:
                    if (cursor < b_end) and (proposed_end > b_start):
                        conflict = True
                        cursor = b_end + timedelta(minutes=5) # Jump over conflict
                        break
                
                if not conflict:
                    # Insert
                    body = {
                        "summary": f"⚔️ Quest: {task.name}", # Gamified Title
                        "description": f"{task.description}\n\nXP Reward: {100 + task.duration//2}",
                        "start": {"dateTime": cursor.isoformat()},
                        "end": {"dateTime": proposed_end.isoformat()},
                    }
                    try:
                        calendar_service.events().insert(calendarId='primary', body=body).execute()
                        time.sleep(0.2) 
                    except Exception as e:
                        print(f"Calendar Insert Error: {e}")

                    cursor = proposed_end + timedelta(minutes=10) # Break
                    scheduled = True
                    tasks_done += 1
                    progress((tasks_done / total_tasks), desc=f"📅 Scheduling: {task.name}")
    
    return "✅ All quests synced to Calendar!"

# ============================================================
# 🎮 MODULE 1: GAME LOGIC & STATE MANAGEMENT
# ============================================================

def init_game_state(plan: CompletePlan) -> List[Dict]:
    """Transforms the static 'CompletePlan' into an interactive 'Game State'."""
    game_tasks = []
    task_id = 0
    difficulties = ["Normal", "Hard", "Hardest"]
    
    for day in plan.daily_plans:
        for task in day.tasks:
            is_boss = "mock" in task.name.lower()
            difficulty = "Hardest" if is_boss else random.choice(difficulties)
            
            # XP Calculation
            base_xp = {"Normal": 50, "Hard": 100, "Hardest": 150}[difficulty]
            duration_xp = task.duration // 2
            xp = base_xp + duration_xp
            if is_boss:
                xp *= 1.5  # 50% multiplier for bosses

            game_tasks.append({
                "id": task_id,
                "day": f"Day {day.day}",
                "name": task.name,
                "desc": task.description,
                "status": "🔓 UNLOCKED" if task_id == 0 else "🔒 LOCKED", 
                "xp_reward": int(xp), 
                "type": "BOSS BATTLE" if is_boss else "QUEST",
                "difficulty": difficulty
            })
            task_id += 1
            
    return game_tasks

def render_quest_board(game_tasks: List[Dict]) -> pd.DataFrame:
    """Converts game state into a clean DataFrame for the UI."""
    data = []
    if not game_tasks:
        return pd.DataFrame(columns=["Status", "Timeline", "Quest Objective", "Rewards"])

    for t in game_tasks:
        status_icon = t['status']
        if t['status'] == "COMPLETED":
            status_icon = "✅ DONE"
        
        name = t['name']
        if t['type'] == "BOSS BATTLE":
            name = f"💀 {name.upper()}"

        data.append([
            status_icon,
            t['day'],
            name,
            f"+{t['xp_reward']} XP"
        ])
    
    return pd.DataFrame(
        data, 
        columns=["Status", "Timeline", "Quest Objective", "Rewards"]
    )

def calculate_player_stats(game_tasks: List[Dict]):
    """Calculates total XP and Level."""
    if not game_tasks:
        return 0, 1, "Novice"
        
    current_xp = sum(t['xp_reward'] for t in game_tasks if t['status'] == "COMPLETED")
    level = 1 + (current_xp // 500)
    titles = ["Novice", "Apprentice", "Journeyman", "Expert", "Master", "Grandmaster"]
    title = titles[min(level-1, len(titles)-1)]
    return current_xp, level, title

# ============================================================
# 🧠 MODULE 2: AI QUIZ ENGINE
# ============================================================

def generate_quiz_for_task(role: str, task_name: str, task_desc: str, difficulty: str) -> List[Dict]:
    """Generates 3-6 multiple-choice questions dynamically based on difficulty."""
    num_questions = random.randint(3, 6)
    
    difficulty_instructions = {
        "Normal": "The questions should be challenging, simulating a real interview question for the role.",
        "Hard": "The questions should be particularly tough, focusing on non-obvious aspects, edge cases, or requiring deep, specific knowledge.",
        "Hardest": "The questions should be exceptionally difficult, suitable for a senior or leadership position in the field. They might involve complex problem-solving, strategic thinking, or deep domain expertise."
    }

    prompt = f"""
    CONTEXT: User is preparing for a '{role}' role.
    CURRENT QUEST: "{task_name}" - {task_desc}
    DIFFICULTY: {difficulty} - {difficulty_instructions.get(difficulty, "")}

    INSTRUCTIONS:
    Generate {num_questions} distinct multiple-choice questions to test the user's understanding of this specific quest.
    
    OUTPUT:
    Return strictly a JSON object with this structure:
    {{
        "questions": [
            {{
                "q": "Question Text?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_index": 0 
            }}, ...
        ]
    }}
    IMPORTANT: "correct_index" must be an Integer (0, 1, 2, or 3) corresponding to the correct option in the list.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        questions = data.get("questions", [])
        
        # Validation to ensure correct_index exists
        for q in questions:
            if "correct_index" not in q:
                q["correct_index"] = 0 # Fallback
                
        return questions
    except Exception as e:
        print(f"Quiz Error: {e}")
        # Fallback
        return [{"q": "Confirm you completed this task?", "options": ["Yes", "No"], "correct_index": 0}] * num_questions

# ============================================================
# 📝 MODULE 3: PLAN PARSING
# ============================================================

def parse_markdown_to_plan(markdown_text: str) -> CompletePlan:
    """Parses the Agent's markdown output into a structured Plan object."""
    lines = markdown_text.split('\n')
    daily_plans = []
    current_day = 0
    current_tasks = []
    summary = "Your custom strategy."

    # Matches: "- 60 mins: **Title** - Description"
    # Added flexibility for spaces/formatting
    task_pattern = re.compile(r'-\s+(\d+)\s*mins?:\s*\*\*(.*?)\*\*\s*-\s*(.*)')
    
    for line in lines:
        line = line.strip()
        
        # Day Header
        day_match = re.search(r'Day\s+(\d+)', line, re.IGNORECASE)
        if day_match and line.startswith('#'):
            if current_day > 0 and current_tasks:
                daily_plans.append(DailyPlan(day=current_day, tasks=current_tasks))
            current_day = int(day_match.group(1))
            current_tasks = []
            continue

        # Task Item
        match = task_pattern.match(line)
        if match:
            current_tasks.append(Task(
                duration=int(match.group(1)),
                name=match.group(2).strip(),
                description=match.group(3).strip()
            ))

    if current_day > 0 and current_tasks:
        daily_plans.append(DailyPlan(day=current_day, tasks=current_tasks))

    return CompletePlan(short_summary=summary, daily_plans=daily_plans)

# ============================================================
# ⚡ MODULE 4: GENERATION LOGIC (Global)
# ============================================================

async def stream_plan_generation(role, goal, hours, start_date_ts, interview_date_ts, use_cal, pref_time, progress=gr.Progress()):
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
    - Logistics: {days_avail} days available, {hours} hours/day.
    
    INSTRUCTIONS:
    Write a gamified preparation plan. Create quests specific to {role}.
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
    
    xp, lvl, title = calculate_player_stats(game_tasks)
    stats_html = f"<div style='text-align:center; padding:10px; background:#f3f4f6; border-radius:8px;'><h2>Level {lvl} {title}</h2><p>✨ {xp} XP Earned</p></div>"

    yield (
        "", gr.update(), gr.update(),
        game_tasks, board_df, stats_html,
        gr.update(visible=False), gr.update(visible=True) # Hide loading, Show Board
    )


# ============================================================
# 🖥️ UI LAYOUT
# ============================================================

css = ".container { max-width: 900px; margin: auto; } .btn-primary { background-color: #4f46e5; color: white; } .feedback { font-weight: bold; font-size: 1.1em; }"

with gr.Blocks(title="Career Quest", css=css) as demo:
    
    # Global State
    game_state_store = gr.State([]) 
    active_task_idx = gr.State(-1)
    active_quiz_data = gr.State([])

    gr.Markdown("# 🚀 Career Quest: Gamified Prep", elem_classes="text-center")

    # --- STEP 1: SETUP ---
    with gr.Column(visible=True) as step_1_col:
        gr.Markdown("### 👤 Character Setup")
        with gr.Row():
            role_input = gr.Textbox(label="Target Role (Class)", placeholder="e.g. Nurse, Python Dev")
            hours_input = gr.Slider(1, 10, value=2, label="Hours per Day")
        
        goal_input = gr.Textbox(label="Main Quest Goal", placeholder="e.g. Land a senior role")
        
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
            quest_board = gr.DataFrame(
                headers=["Status", "Timeline", "Quest Objective", "Rewards"],
                datatype=["str", "str", "str", "str"],
                interactive=False
                # selection_mode Removed for compatibility
            )
            board_feedback = gr.Textbox(label="System Log", interactive=False)

        # Container for the Quiz Overlay (Hidden by default)
        with gr.Group(visible=False) as quiz_modal:
            gr.Markdown("## 🧠 Knowledge Check")
            q_header = gr.Markdown("Loading...")
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

    def on_quest_click(evt: gr.SelectData, game_tasks, role):
        """Handles clicking a Quest on the board."""
        if not evt or not game_tasks: 
            return {board_feedback: "⚠️ No task selected"}
        
        row_idx = evt.index[0]
        # Safety check for index
        if row_idx >= len(game_tasks):
            return {board_feedback: "⚠️ Error: Invalid Task Selection"}

        task = game_tasks[row_idx]
        
        if task['status'] == "🔒 LOCKED":
            return {quiz_modal: gr.update(visible=False), board_feedback: "🚫 Quest Locked! Complete previous quests first."}
        
        if task['status'] == "COMPLETED":
            return {quiz_modal: gr.update(visible=False), board_feedback: "✅ Quest already completed!"}

        # Generate Quiz
        quiz_questions = generate_quiz_for_task(role, task['name'], task['desc'], task['difficulty'])
        
        num_questions = len(quiz_questions)

        # Debug Print
        print(f"Generated {num_questions} Quiz for {task['name']} (Difficulty: {task['difficulty']})")
        for q in quiz_questions:
            print(f"Q: {q['q']} | Ans: {q['options'][q['correct_index']]}")

        updates = {
            board_container: gr.update(visible=False),
            quiz_modal: gr.update(visible=True),
            active_task_idx: row_idx,
            active_quiz_data: quiz_questions,
            q_header: gr.update(value=f"### ⚔️ Quest: {task['name']}"),
            feedback_box: gr.update(value="")
        }
        
        # Dynamically update question components
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

        return updates

    def submit_quiz_answers(idx, a1, a2, a3, a4, a5, a6, quiz_data, game_tasks):
        if idx == -1 or not game_tasks:
            return {feedback_box: "⚠️ Error: No active quest."}

        num_questions = len(quiz_data)
        user_answers = [a1, a2, a3, a4, a5, a6]
        
        # Debug Inputs
        print(f"Submit Answers: {user_answers[:num_questions]}")

        # Validation Logic
        score = 0
        for i, question in enumerate(quiz_data):
            correct_idx = question.get('correct_index', 0)
            options = question.get('options', [])
            
            if 0 <= correct_idx < len(options):
                correct_string = options[correct_idx]
                user_ans = user_answers[i]
                if user_ans and user_ans.strip() == correct_string.strip():
                    score += 1
                else:
                    print(f"Wrong Answer for Q{i+1}: User '{user_ans}' vs Correct '{correct_string}'")
            else:
                print(f"Error: Index {correct_idx} out of bounds for options {options}")

        # Fail Condition (needs 2/3 majority to pass)
        pass_threshold = -(-num_questions * 2 // 3) # Ceiling division
        if score < pass_threshold:
            return {
                feedback_box: f"❌ {score}/{num_questions} Correct. You need {pass_threshold} to pass. Try again!",
                board_container: gr.update(visible=False),
                quiz_modal: gr.update(visible=True),
                game_state_store: game_tasks,
                quest_board: gr.update(),
                stats_display: gr.update()
            }
        
        # Success Logic
        game_tasks[idx]['status'] = "COMPLETED"
        if idx + 1 < len(game_tasks):
            game_tasks[idx + 1]['status'] = "🔓 UNLOCKED"
            
        xp, lvl, title = calculate_player_stats(game_tasks)
        new_stats = f"<div style='text-align:center; padding:10px; background:#dcfce7; border-radius:8px;'><h2>Level {lvl} {title}</h2><p>✨ {xp} XP Earned</p></div>"
        new_df = render_quest_board(game_tasks)
        
        return {
            feedback_box: "🎉 Victory! Next Quest Unlocked.",
            board_container: gr.update(visible=True),
            quiz_modal: gr.update(visible=False),
            game_state_store: game_tasks,
            quest_board: gr.update(value=new_df),
            stats_display: gr.update(value=new_stats),
            board_feedback: "✅ Quest Complete!"
        }

    # --- WIRING ---
    generate_btn.click(
        fn=stream_plan_generation,
        inputs=[role_input, goal_input, hours_input, start_date, interview_date, use_cal, pref_time],
        outputs=[raw_stream_output, step_1_col, step_2_col, game_state_store, quest_board, stats_display, loading_msg, board_container]
    )

    quest_board.select(
        fn=on_quest_click,
        inputs=[game_state_store, role_input],
        outputs=[board_container, quiz_modal, active_task_idx, active_quiz_data, q_header, q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp, feedback_box, board_feedback]
    )

    submit_quiz_btn.click(
        fn=submit_quiz_answers,
        inputs=[active_task_idx, q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp, active_quiz_data, game_state_store],
        outputs=[feedback_box, board_container, quiz_modal, game_state_store, quest_board, stats_display, board_feedback]
    )

if __name__ == "__main__":
    gr.mount_gradio_app(app, demo, path="/")
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)