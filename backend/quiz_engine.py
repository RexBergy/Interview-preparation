
import json
import random
from typing import List, Dict

from openai import OpenAI

client = OpenAI()

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
