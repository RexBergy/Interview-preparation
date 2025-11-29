from datetime import datetime
from typing import Dict, Any, AsyncGenerator

from fastapi import Request

from openai.types.responses import ResponseTextDeltaEvent
from agents import Runner
from backend.calendar_utils import smart_schedule_quests, calendar_service, connect, oauth2callback
from backend.game_logic import init_game_state, render_quest_board, calculate_player_stats
from backend.local_agents.writer import writer_agent
from backend.plan_parser import parse_markdown_to_plan
from backend.quiz_engine import generate_quiz_for_task

async def generate_and_initialize_plan(
    game_state: Dict[str, Any],
    role: str,
    goal: str,
    job_description: str,
    hours: int,
    start_date: str,
    interview_date: str,
    use_cal: bool,
    pref_time: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handles the entire plan generation process, from calling the agent to initializing the game state.
    This function is a generator that yields events for streaming to the client.
    """
    # 1. Generate Plan from Agent
    system_prompt = f"""
    CONTEXT:
    - Candidate Role: {role}
    - Goals: {goal}
    - Job Description: {job_description if job_description else "Not provided."}
    - Logistics: {(datetime.fromisoformat(interview_date) - datetime.fromisoformat(start_date)).days} days available, {hours} hours/day.
    INSTRUCTIONS:
    Write a gamified preparation plan. Create quests specific to the role of {role}.
    If a job description is provided, tailor the quests to the requirements and responsibilities listed.
    The quests should cover both general skills for the role and specific points from the job description.
    Format carefully as requested.
    """
    full_response = ""
    result = Runner.run_streamed(writer_agent, system_prompt)
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            delta = event.data.delta or ""
            full_response += delta
            yield {"event": "plan_chunk", "data": delta}

    # 2. Parse and Initialize Game
    plan_obj = parse_markdown_to_plan(full_response)
    game_state["tasks"] = init_game_state(plan_obj)
    game_state["player_lives"] = 3

    # 3. Calendar Sync (if requested)
    if use_cal and calendar_service:
        yield {"event": "status", "data": "Syncing with Google Calendar..."}
        start_dt = datetime.fromisoformat(start_date)
        await smart_schedule_quests(plan_obj, start_dt, int(pref_time))

    yield {"event": "complete", "data": "Plan generated successfully!"}


def get_calendar_connect_url() -> str:
    """Gets the Google Calendar authentication URL."""
    return connect()


async def handle_calendar_oauth_callback(request: Request):
    """Handles the OAuth2 callback from Google."""
    return await oauth2callback(request)


def get_current_game_state(game_state: Dict[str, Any]) -> Dict[str, Any] | None:
    """Renders the current board and player stats from the game state."""
    if not game_state["tasks"]:
        return None

    board_df = render_quest_board(game_state["tasks"])
    xp, lvl, title, xp_in_level, xp_per_level = calculate_player_stats(game_state["tasks"])

    return {
        "board": board_df.to_dict(orient="records"),
        "stats": {
            "xp": xp, "level": lvl, "title": title,
            "xp_in_level": xp_in_level, "xp_per_level": xp_per_level,
            "lives": game_state["player_lives"]
        }
    }


def start_new_quiz(game_state: Dict[str, Any], task_index: int, role: str) -> Dict[str, Any]:
    """Generates a quiz for a specific task and updates the game state."""
    task = game_state["tasks"][task_index]
    quiz_questions = generate_quiz_for_task(role, task['name'], task['desc'], task['difficulty'])
    game_state["active_quiz"] = quiz_questions
    game_state["active_task_idx"] = task_index

    client_questions = [{k: v for k, v in q.items() if k != 'correct_index'} for q in quiz_questions]
    return {"questions": client_questions, "task_name": task['name']}

def process_quiz_submission(game_state: Dict[str, Any], user_answers: list) -> Dict[str, Any]:
    """
    Processes the user's quiz answers, updates the game state, and returns the result.
    """
    idx = game_state["active_task_idx"]
    quiz_data = game_state["active_quiz"]

    score = 0
    for i, question in enumerate(quiz_data):
        correct_answer = question["options"][question["correct_index"]]
        if i < len(user_answers) and user_answers[i] == correct_answer:
            score += 1

    pass_threshold = -(-len(quiz_data) * 2 // 3)  # Ceiling division

    if score >= pass_threshold:
        game_state["tasks"][idx]['status'] = "COMPLETED"
        if idx + 1 < len(game_state["tasks"]):
            game_state["tasks"][idx + 1]['status'] = "🔓 UNLOCKED"
        return {"passed": True, "score": score, "total": len(quiz_data)}
    else:
        game_state["player_lives"] -= 1
        result = {"passed": False, "score": score, "total": len(quiz_data), "lives_left": game_state["player_lives"]}
        if game_state["player_lives"] <= 0:
            result["game_over"] = True
        return result