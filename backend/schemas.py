# backend/schemas.py

"""
Pydantic Models for API Data Validation

This module defines the Pydantic schemas used for validating the data structures
of incoming API requests and, where necessary, outgoing responses. By using these
models, the application ensures type safety, data integrity, and clear, self-documenting
API contracts.
"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class PlanRequest(BaseModel):
    """
    Defines the expected data structure for a request to generate a new study plan.
    This model is used to validate the input from the user's initial setup form.
    """
    role: str = Field(..., description="The user's target job role (e.g., 'Software Engineer').")
    job_description: Optional[str] = Field(None, description="An optional, detailed job description for creating a highly tailored plan.")
    hours: float = Field(..., gt=0, description="The number of hours the user commits to studying per day.")
    start_date: date = Field(..., description="The date the user intends to begin their study plan.")
    interview_date: date = Field(..., description="The scheduled date of the user's interview.")
    use_cal: bool = Field(False, description="Flag to indicate if the user wants to sync the plan with Google Calendar.")
    pref_time: int = Field(..., ge=0, le=23, description="The user's preferred hour for studying, in 24-hour format.")

class QuizStartRequest(BaseModel):
    """
    Defines the data structure for a request to start a new quiz for a specific task.
    """
    task_index: int = Field(..., ge=0, description="The zero-based index of the task (quest) to start the quiz for.")
    role: str = Field(..., description="The user's target role, used to generate relevant quiz questions.")

class QuizSubmitRequest(BaseModel):
    """
    Defines the data structure for a request to submit quiz answers for evaluation.
    """
    answers: List[str] = Field(..., description="An ordered list of the user's selected answers for the active quiz.")

class TrainRequest(BaseModel):
    """
    Defines the data structure for a request to get training materials for a specific task.
    """
    quest: str = Field(..., description="The description of the task to get training materials for.")
