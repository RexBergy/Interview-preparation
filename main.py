
import os
from typing import  Dict, Any

from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.game_manager import (
    generate_and_initialize_plan,
    process_quiz_submission,
    get_calendar_connect_url,
    handle_calendar_oauth_callback,
    get_current_game_state,
    start_new_quiz
)

# When running locally, disable OAuthlib's HTTPs verification.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI()

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# --- Globals for Game State ---
game_state: Dict[str, Any] = {
    "tasks": [],
    "player_lives": 3,
    "active_quiz": [],
    "active_task_idx": -1
}

class PlanRequest(BaseModel):
    role: str
    goal: str
    job_description: str | None = None
    hours: int
    start_date: str
    interview_date: str
    use_cal: bool
    pref_time: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("frontend/index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/connect_calendar")
def connect_calendar():
    auth_url = get_calendar_connect_url()
    return {"auth_url": auth_url}

@app.get("/oauth2callback", response_class=HTMLResponse)
async def handle_oauth2callback(request: Request):
    return await handle_calendar_oauth_callback(request)

@app.post("/generate_plan")
async def generate_plan(req: PlanRequest):
    # The logic is now delegated to a manager function.
    event_generator = generate_and_initialize_plan(
        game_state=game_state,
        role=req.role,
        goal=req.goal,
        job_description=req.job_description,
        hours=req.hours,
        start_date=req.start_date,
        interview_date=req.interview_date,
        use_cal=req.use_cal,
        pref_time=req.pref_time,
    )
    return EventSourceResponse(event_generator)

@app.get("/game_state")
def get_game_state():
    state_data = get_current_game_state(game_state)
    if not state_data:
        return JSONResponse({"error": "Game not initialized"}, status_code=404)
    return state_data

@app.post("/start_quiz")
def start_quiz(body: Dict = Body(...)):
    idx = body.get("task_index")
    role = body.get("role")
    if idx is None or not role or idx >= len(game_state["tasks"]):
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    return start_new_quiz(game_state, idx, role)

@app.post("/quiz/submit")
def submit_quiz(body: Dict = Body(...)):
    user_answers = body.get("answers", [])

    if game_state["active_task_idx"] == -1 or not game_state["active_quiz"]:
        return JSONResponse({"error": "No active quiz"}, status_code=400)

    # Delegate quiz processing to the manager function.
    result = process_quiz_submission(game_state, user_answers)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)
