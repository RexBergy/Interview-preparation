# backend/training_engine.py

"""
Dynamically generates training material using an AI model.

This module is responsible for creating an explanation and a list of
resources for a specific task. It interfaces with an AI model (like GPT-4)
to generate relevant and helpful training material and ensures the output
is in a valid JSON format.
"""

import json
from typing import Dict, Any, List

from openai import OpenAI

# --- AI Configuration ---

# Initialize the OpenAI client.
# It is assumed that the OPENAI_API_KEY environment variable is set.
client = OpenAI()

def generate_training_material(task_name: str, task_desc: str) -> Dict[str, Any]:
    """
    Generates training material for a given task using an AI model.

    Args:
        task_name: The name of the task (quest) to be explained.
        task_desc: The description of the task.

    Returns:
        A dictionary containing an 'explanation' and a list of 'resources'.
        Returns fallback material if the AI fails.
    """
    system_prompt = _build_training_prompt(task_name, task_desc)

    try:
        # Request a JSON response from the AI model.
        response = client.chat.completions.create(
            model="gpt-4o", # Using a powerful model for better quality.
            messages=[{"role": "user", "content": system_prompt}],
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI response content is empty.")

        data = json.loads(content)
        
        # Validate the structure of the returned data.
        if "explanation" not in data or "resources" not in data:
            raise ValueError("Invalid or incomplete JSON structure in AI response.")

        return data

    except (json.JSONDecodeError, ValueError, Exception) as e:
        print(f"Error generating training material from AI: {e}. Using fallback material.")
        # Provide simple fallback material in case of any errors.
        return {
            "explanation": "Could not generate a detailed explanation. Please refer to standard documentation on this topic.",
            "resources": ["https://www.google.com/search?q=" + task_name.replace(" ", "+")]
        }

def _build_training_prompt(task_name: str, task_desc: str) -> str:
    """Constructs the detailed prompt for the AI to generate training material."""
    
    return f"""
    CONTEXT:
    A user is trying to learn about a topic for an interview.
    The topic is named "{task_name}", which is described as: "{task_desc}".

    INSTRUCTIONS:
    Your task is to generate a clear, concise explanation of this topic.
    You should also provide a list of 2-3 high-quality online resources (articles, tutorials, documentation) that the user can study.

    OUTPUT FORMAT:
    You MUST return a single, valid JSON object with the following structure. Do not include any other text or explanations.
    {{
        "explanation": "A detailed but easy-to-understand explanation of the concept, covering the key points.",
        "resources": [
            "https://example.com/resource1",
            "https://example.com/resource2"
        ]
    }}
    
    IMPORTANT: Ensure the resources are real, relevant, and high-quality URLs.
    """
