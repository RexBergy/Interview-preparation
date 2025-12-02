# backend/game_manager.py

"""
Manages the core game state and logic for the Interview Quest application.

This class is responsible for:
- Generating and parsing the user's personalized study plan.
- Initializing and maintaining the game state (tasks, player lives).
- Handling quiz generation, submission, and grading.
- Calculating player statistics (XP, level, etc.).
- Interacting with other modules like the AI agent, calendar, and quiz engine.

The GameManager is designed to be a singleton within the request-response cycle,
managed by FastAPI's dependency injection system.
"""

from datetime import datetime
from typing import Dict, Any, AsyncGenerator, List, Tuple
import json
import asyncio # Import asyncio

from agents import Runner
from fastapi import HTTPException
from openai.types.responses import ResponseTextDeltaEvent

from backend.calendar_utils import smart_schedule_quests, request_calendar_service
from backend.game_logic import init_game_state, render_quest_board, calculate_player_stats
from backend.local_agents.writer import writer_agent
from backend.plan_parser import parse_markdown_to_plan
from backend.quiz_engine import generate_quiz_for_task, QUIZ_PASS_THRESHOLD
from backend.training_engine import generate_training_material
from backend.schemas import PlanRequest


class GameManager:
    """
    Manages the game state, including tasks, player stats, and active quizzes.
    """
    def __init__(self):
        """Initializes the GameManager with a default, empty state."""
        self.tasks: List[Dict[str, Any]] = []
        self.active_quiz: List[Dict[str, Any]] = []
        self.active_task_idx: int = -1
        self.quizzes: Dict[int, List[Dict[str, Any]]] = {}
        self.training_materials: Dict[int, Any] = {}

    def reset_game_state(self):
        """Resets the game state to its initial default values."""
        self.tasks = []
        self.active_quiz = []
        self.active_task_idx = -1
        self.quizzes = {}
        self.training_materials = {}

    async def generate_and_initialize_plan(
        self, req: PlanRequest
    ) -> AsyncGenerator[str, None]:
        """
        Generates, parses, and initializes a new study plan.

        This asynchronous generator method performs the following steps:
        1. Resets the current game state.
        2. Constructs a detailed prompt for the AI agent based on user input.
        3. Streams the AI-generated plan back to the client via Server-Sent Events (SSE).
        4. Parses the complete markdown plan into a structured object.
        5. Initializes the game state (tasks and player lives) based on the plan.
        6. If requested, syncs the quests with the user's Google Calendar.

        Args:
            req (PlanRequest): The Pydantic model containing all user inputs for plan generation.

        Yields:
            str: JSON-formatted Server-Sent Events (SSE) for streaming to the client.
                 Events can be of type 'plan_chunk', 'status', or 'complete'.
        """
        self.reset_game_state()

        # Step 1: Generate a detailed prompt for the AI agent.
        system_prompt = self._build_system_prompt(req)
        
        yield self._sse_event("status", "Generating your personalized quest plan...")

        # Step 2: Stream the response from the AI writer agent.
        full_response = ""
        result = Runner.run_streamed(writer_agent, system_prompt)
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                delta = event.data.delta or ""
                full_response += delta
                yield self._sse_event("plan_chunk", delta)
        
        yield self._sse_event("status", "Parsing and initializing game board...")

        # Step 3: Parse the markdown plan and initialize the game state.
        try:
            plan_obj = parse_markdown_to_plan(full_response)
            self.tasks = init_game_state(plan_obj)
        except (ValueError, KeyError) as e:
            yield self._sse_event("error", f"Failed to parse the generated plan: {e}")
            return
        
        calendar_service = request_calendar_service()

        # Step 4: Sync with Google Calendar if requested and available.
        print("Attempting to sync with Google Calendar...", req.use_cal, calendar_service)
        if req.use_cal and calendar_service:
            yield self._sse_event("status", "Syncing with Google Calendar...")
            try:
                print("Attempting to sync with Google Calendar...")
                await smart_schedule_quests(plan_obj, req.start_date, req.pref_time)
                yield self._sse_event("status", "Calendar sync complete!")
            except Exception as e:
                # Non-critical error, so we just inform the user.
                yield self._sse_event("status", f"Calendar sync failed: {e}")

        yield self._sse_event("complete", "Plan generated successfully!")
        
        # Preload only the first quiz if tasks exist
        if self.tasks:
            yield self._sse_event("status", "Preloading the first quiz for your quests...")
            idx = 0
            task = self.tasks[idx]
            try:
                quiz_questions = generate_quiz_for_task(
                    req.role,
                    task['name'],
                    task['desc'],
                    task['difficulty']
                )
                self.quizzes[idx] = quiz_questions
                yield self._sse_event("quiz_preloaded", {"task_index": idx, "status": "success"})
            except Exception as e:
                print(f"Error preloading quiz for task {idx}: {e}")
                yield self._sse_event("quiz_preloaded", {"task_index": idx, "status": "error", "message": str(e)})
            yield self._sse_event("complete", "First quiz preloaded!")
        
        # Preload only the first training material if tasks exist
        if self.tasks:
            yield self._sse_event("status", "Preloading the first training material for your quests...")
            idx = 0
            task = self.tasks[idx]
            try:
                training_material = generate_training_material(
                    task['name'],
                    task['desc']
                )
                self.training_materials[idx] = training_material
                yield self._sse_event("training_preloaded", {"task_index": idx, "status": "success"})
            except Exception as e:
                print(f"Error preloading training material for task {idx}: {e}")
                yield self._sse_event("training_preloaded", {"task_index": idx, "status": "error", "message": str(e)})
            yield self._sse_event("complete", "First training material preloaded!")

    def get_current_game_state(self) -> Dict[str, Any] | None:
        """
        Calculates and returns the current state of the game.

        If the game is not initialized (i.e., no tasks), it returns None.
        Otherwise, it computes the player's stats and formats the quest board.

        Returns:
            A dictionary containing the rendered 'board' and player 'stats',
            or None if the game has not been initialized.
        """
        if not self.tasks:
            return None

        board_df = render_quest_board(self.tasks)
        stats = calculate_player_stats(self.tasks)

        return {
            "board": board_df.to_dict(orient="records"),
            "stats": {
                "xp": stats["xp"],
                "level": stats["level"],
                "title": stats["title"],
                "xp_in_level": stats["xp_in_level"],
                "xp_per_level": stats["xp_per_level"],
            },
        }

    async def start_new_quiz(self, task_index: int, role: str) -> Dict[str, Any]:
        """
        Generates a new quiz for a given task and sets it as the active quiz.

        Args:
            task_index: The index of the task to generate the quiz for.
            role: The user's role, used to tailor quiz questions.

        Returns:
            A dictionary containing the quiz questions (without answers) and the task name,
            ready to be sent to the client.
        """
        if task_index >= len(self.tasks):
            raise ValueError(f"Task index {task_index} is out of bounds.")

        task = self.tasks[task_index] # Moved task assignment here

        if task_index not in self.quizzes:
            try:
                # Generate the quiz on demand
                quiz_questions = generate_quiz_for_task(
                    role,
                    task['name'],
                    task['desc'],
                    task['difficulty']
                )
                self.quizzes[task_index] = quiz_questions
                print(f"Quiz for task index {task_index} generated on demand.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate quiz for task {task_index}: {e}")

        quiz_questions = self.quizzes[task_index]
        
        if not isinstance(quiz_questions, list):
            raise HTTPException(status_code=500, detail=f"Quiz data for task {task_index} is corrupted or not a list.")
        
        self.active_quiz = quiz_questions
        self.active_task_idx = task_index

        # Filter out the correct answer and justification before sending to the client.
        client_questions = [
            {k: v for k, v in q.items() if k not in ['correct_index', 'justification']}
            for q in quiz_questions
        ]

        # Trigger preloading of the next quiz in the background
        if task_index + 1 < len(self.tasks) and (task_index + 1) not in self.quizzes:
            asyncio.create_task(self._preload_quiz_background(task_index + 1, role))

        # Trigger preloading of the next training material in the background
        if task_index + 1 < len(self.tasks) and (task_index + 1) not in self.training_materials:
            asyncio.create_task(self._preload_training_background(task_index + 1))
            
        return {"questions": client_questions, "task_name": task['name']}

    async def _preload_quiz_background(self, task_index: int, role: str):
        """
        Asynchronously preloads a quiz for a given task in the background.
        """
        if task_index >= len(self.tasks):
            return

        if task_index not in self.quizzes:
            task = self.tasks[task_index]
            try:
                quiz_questions = generate_quiz_for_task(
                    role,
                    task['name'],
                    task['desc'],
                    task['difficulty']
                )
                self.quizzes[task_index] = quiz_questions
                print(f"Background: Quiz for task index {task_index} preloaded successfully.")
            except Exception as e:
                print(f"Background: Error preloading quiz for task {task_index}: {e}")

    async def _preload_training_background(self, task_index: int):
        """
        Asynchronously preloads training material for a given task in the background.
        """
        if task_index >= len(self.tasks):
            return

        if task_index not in self.training_materials:
            task = self.tasks[task_index]
            try:
                training_material = generate_training_material(
                    task['name'],
                    task['desc']
                )
                self.training_materials[task_index] = training_material
                print(f"Background: Training material for task index {task_index} preloaded successfully.")
            except Exception as e:
                print(f"Background: Error preloading training material for task {task_index}: {e}")

    def process_quiz_submission(self, user_answers: List[str]) -> Dict[str, Any]:
        """
        Processes the user's answers for the active quiz, updates the game state,
        and returns the result.

        Args:
            user_answers: A list of the user's selected answers.

        Returns:
            A dictionary containing the quiz result, including whether the user passed,
            their score, and their remaining lives.
        """
        idx = self.active_task_idx
        quiz_data = self.active_quiz

        score = self._grade_quiz(user_answers, quiz_data)
        passed = score >= QUIZ_PASS_THRESHOLD * len(quiz_data)

        if passed:
            self.tasks[idx]['status'] = "COMPLETED"
            # Unlock the next task if it exists
            if idx + 1 < len(self.tasks):
                self.tasks[idx + 1]['status'] = "UNLOCKED"
            return {
                "passed": True,
                "score": score,
                "total": len(quiz_data),
                "quiz_data": quiz_data,
            }
        else:
            self.tasks[idx]['lives'] -= 1
            result = {
                "passed": False,
                "score": score,
                "total": len(quiz_data),
                "lives_left": self.tasks[idx]['lives'],
            }
            if self.tasks[idx]['lives'] <= 0:
                result["game_over"] = True
                result["quiz_data"] = quiz_data
            return result

    def _build_system_prompt(self, req: PlanRequest) -> str:
        """Constructs the system prompt for the AI agent."""
        days_available = (req.interview_date - req.start_date).days
        return f"""
        CONTEXT:
        - Candidate Role: {req.role}
        - Job Description: {req.job_description if req.job_description else "Not provided."}
        - Logistics: {days_available} days available, {req.hours} hours/day.
        
        INSTRUCTIONS:
        Write a gamified preparation plan. Create quests specific to the role of {req.role}.
        If a job description is provided, tailor the quests to the requirements and responsibilities listed.
        The quests should cover both general skills for the role and specific points from the job description.
        Format the output as a clean, structured markdown document.
        """

    def _sse_event(self, event_type: str, data: Any) -> str:
        """Formats data as a Server-Sent Event string."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    def _grade_quiz(self, user_answers: List[str], quiz_data: List[Dict[str, Any]]) -> int:
        """Compares user answers to the correct answers and returns the score."""
        score = 0
        for i, question in enumerate(quiz_data):
            correct_answer = question["options"][question["correct_index"]]
            if i < len(user_answers) and user_answers[i] == correct_answer:
                score += 1
        return score