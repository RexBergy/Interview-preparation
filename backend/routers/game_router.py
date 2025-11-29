# backend/routers/game_router.py

"""
API router for handling the core game logic of Interview Quest.

This router provides endpoints for generating a study plan, getting the game state,
starting a quiz, and submitting quiz answers.
"""

from fastapi import APIRouter, Depends, Body, HTTPException
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import JSONResponse

from backend.dependencies import get_game_manager
from backend.game_manager import GameManager
from backend.schemas import PlanRequest, QuizStartRequest, QuizSubmitRequest

# Create an API router for game-related endpoints.
router = APIRouter()


@router.post("/generate_plan", summary="Generate a Personalized Study Plan")
async def generate_plan(req: PlanRequest, manager: GameManager = Depends(get_game_manager)):
    """
    Generates a new, personalized study plan based on user inputs.

    This endpoint streams the plan generation process back to the client using
    Server-Sent Events (SSE), providing real-time updates on the progress.

    Args:
        req (PlanRequest): The user's input for generating the plan.
        manager (GameManager): The dependency-injected game manager instance.

    Returns:
        EventSourceResponse: A streaming response of server-sent events.
    """
    event_generator = manager.generate_and_initialize_plan(req)
    return EventSourceResponse(event_generator)


@router.get("/game_state", summary="Get the Current Game State")
def get_game_state(manager: GameManager = Depends(get_game_manager)):
    """
    Retrieves the current state of the game, including player stats and the quest board.

    Args:
        manager (GameManager): The dependency-injected game manager instance.

    Returns:
        dict: The current game state if initialized.
    
    Raises:
        HTTPException: 404 if the game has not been initialized.
    """
    state_data = manager.get_current_game_state()
    if not state_data:
        raise HTTPException(status_code=404, detail="Game not initialized. Please generate a plan first.")
    return state_data


@router.post("/start_quiz", summary="Start a New Quiz for a Task")
def start_quiz(req: QuizStartRequest, manager: GameManager = Depends(get_game_manager)):
    """
    Initiates a new quiz for a specific task on the quest board.

    Args:
        req (QuizStartRequest): The request body containing the task index and role.
        manager (GameManager): The dependency-injected game manager instance.

    Returns:
        dict: The quiz questions and task name.

    Raises:
        HTTPException: 400 if the task index is invalid.
    """
    if not (0 <= req.task_index < len(manager.tasks)):
        raise HTTPException(status_code=400, detail="Invalid task index.")

    return manager.start_new_quiz(req.task_index, req.role)


@router.post("/quiz/submit", summary="Submit Answers for the Active Quiz")
def submit_quiz(req: QuizSubmitRequest, manager: GameManager = Depends(get_game_manager)):
    """
    Submits the user's answers for the currently active quiz and returns the result.

    Args:
        req (QuizSubmitRequest): The request body containing the user's answers.
        manager (GameManager): The dependency-injected game manager instance.

    Returns:
        dict: The result of the quiz submission, including score and pass/fail status.

    Raises:
        HTTPException: 400 if there is no active quiz to submit to.
    """
    if manager.active_task_idx == -1 or not manager.active_quiz:
        raise HTTPException(status_code=400, detail="No active quiz found.")

    result = manager.process_quiz_submission(req.answers)
    return result