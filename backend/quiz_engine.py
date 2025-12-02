# backend/quiz_engine.py

"""
Dynamically generates quizzes using an AI model.

This module is responsible for creating a set of multiple-choice questions
based on a user's role, a specific task, and a desired difficulty level.
It interfaces with an AI model (like GPT-4) to generate relevant and
challenging questions and ensures the output is in a valid JSON format.
"""

import json
import random
from typing import List, Dict, Any

from openai import OpenAI

# --- Constants ---

# The proportion of correct answers required to pass a quiz.
# e.g., 0.67 means the user must answer at least 2/3 of the questions correctly.
QUIZ_PASS_THRESHOLD = 0.67

# --- AI Configuration ---

# Initialize the OpenAI client.
# It is assumed that the OPENAI_API_KEY environment variable is set.
client = OpenAI()

# A dictionary defining the instructions for the AI based on difficulty.
DIFFICULTY_INSTRUCTIONS = {
    "Normal": "The questions should be challenging, simulating a real interview question for the role.",
    "Hard": "The questions should be particularly tough, focusing on non-obvious aspects, edge cases, or requiring deep, specific knowledge.",
    "Hardest": "The questions should be exceptionally difficult, suitable for a senior or leadership position. They might involve complex problem-solving or strategic thinking.",
}

def generate_quiz_for_task(role: str, task_name: str, task_desc: str, difficulty: str) -> List[Dict[str, Any]]:
    """
    Generates a list of multiple-choice questions for a given task using an AI model.

    Args:
        role: The user's target job role.
        task_name: The name of the task (quest) to be tested.
        task_desc: The description of the task.
        difficulty: The desired difficulty of the questions ('Normal', 'Hard', 'Hardest').

    Returns:
        A list of dictionaries, where each dictionary represents a single question
        with its options and the index of the correct answer. Returns a fallback
        question if the AI fails.
    """
    num_questions = random.randint(3, 5) # Generate 3-5 questions per quiz.
    
    system_prompt = _build_quiz_prompt(role, task_name, task_desc, difficulty, num_questions)

    try:
        # Request a JSON response from the AI model.
        response = client.chat.completions.create(
            model="gpt-4o", # Using a powerful model for better question quality.
            messages=[{"role": "user", "content": system_prompt}],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI response content is empty.")

        data = json.loads(content)
        questions = data.get("questions", [])
        
        # Validate the structure of the returned questions.
        if not questions or not all("correct_index" in q for q in questions):
            raise ValueError("Invalid or incomplete JSON structure in AI response.")

        return questions

    except (json.JSONDecodeError, ValueError, Exception) as e:
        print(f"Error generating quiz from AI: {e}. Using fallback question.")
        # Provide a simple fallback question in case of any errors.
        return [
            {
                "q": "This is a fallback question. Please confirm you have completed the task.",
                "options": ["Yes, I completed it", "No, I did not"],
                "correct_index": 0
            }
        ] * num_questions

def _build_quiz_prompt(role: str, task_name: str, task_desc: str, difficulty: str, num_questions: int) -> str:
    """Constructs the detailed prompt for the AI to generate quiz questions."""
    
    difficulty_text = DIFFICULTY_INSTRUCTIONS.get(difficulty, "")
    
    return f"""
    CONTEXT:
    The user is preparing for an interview for a '{role}' position.
    They have just completed a study quest named "{task_name}", which is described as: "{task_desc}".
    The desired difficulty for the quiz is: {difficulty} - {difficulty_text}

    INSTRUCTIONS:
    Your task is to generate {num_questions} distinct, high-quality multiple-choice questions to test the user's understanding of the completed quest.
    For each question, provide a brief justification for the correct answer. This justification will be shown to the user after the quiz.
    The questions must be directly relevant to the quest's topic and appropriate for the specified role and difficulty.

    OUTPUT FORMAT:
    You MUST return a single, valid JSON object with the following structure. Do not include any other text or explanations.
    {{
        "questions": [
            {{
                "q": "The question text goes here.",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_index": 0,
                "justification": "A brief explanation of why this is the correct answer."
            }},
            // ... more question objects
        ]
    }}
    
    IMPORTANT: The "correct_index" field is mandatory and must be an integer (0, 1, 2, or 3) representing the index of the correct answer in the "options" list. The "justification" field is also mandatory.
    """
