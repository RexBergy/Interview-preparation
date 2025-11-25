from pydantic import BaseModel
from agents import Agent

# ==========================================
# 📝 WRITER AGENT CONFIGURATION
# ==========================================

WRITER_PROMPT = """
You are an expert personalized career coach and curriculum designer. 
Your goal is to create a highly engaging, gamified learning path for a candidate preparing for a specific job interview.

# CONTEXT
The candidate needs a structured plan that covers:
1. Hard Skills (Technical knowledge specific to the role)
2. Soft Skills (Behavioral questions, culture fit, communication)
3. Company Research (Understanding the target company)

# INSTRUCTIONS
1. Analyze the User's Role and Goals deeply.
2. Create a daily plan where every "Task" is a distinct "Quest".
3. Keep task descriptions actionable and concise (10-20 words).
4. ENSURE VARIETY:  Include tasks like "Draft STAR stories", "Research Competitors", "Mock Negotiation", etc.

# OUTPUT FORMAT
Create a plan in STRICT MARKDOWN format.
Format every day exactly like this:

# Day 1
- 60 mins: **Quest Title** - Actionable description of the quest.
- 30 mins: **Quest Title** - Actionable description.

# Day 2
...
"""

# ==========================================
# 🏗️ DATA MODELS
# ==========================================

class Task(BaseModel):
    name: str
    """Name of the task/quest (e.g., 'Mastering SQL Joins' or 'STAR Method Practice')."""

    description: str
    """Actionable description (10-20 words)."""

    duration: int
    """Duration in minutes."""

class DailyPlan(BaseModel):
    day: int
    """Day number in the sequence."""

    tasks: list[Task]
    """List of quests for this day."""

class CompletePlan(BaseModel):
    short_summary: str
    """A 1-sentence 'Mission Objective' for the user."""

    daily_plans: list[DailyPlan]
    """The full timeline of daily quests."""

# ==========================================
# 🤖 AGENT DEFINITION
# ==========================================

writer_agent = Agent(
    name="PlanWriterAgent",
    instructions=WRITER_PROMPT,
    model="gpt-4o", # Updated to fast/high-quality model
    tools=[]
)