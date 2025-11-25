from pydantic import BaseModel

from agents import Agent, WebSearchTool

# Writer agent brings together the raw search results and optionally calls out
# to sub‑analyst tools for specialized commentary, then returns a cohesive markdown report.
WRITER_PROMPT = """
You are an expert interview preparation plan writer. Your task is to create a comprehensive, extensive,
detailed plan to prepare a candidate for an upcoming job interview based on 
the candidate profile, job description and any additional candidate information. 

# Instructions
1. Create a daily plan that breaks down the preparation into manageable tasks
2. Make sure to incllude relevent sources, books websites to further research
3. The task descriptions should be between 10 and 20 words. They should include sources for further reading.

# Output:
Create a plan in STRICT MARKDOWN format.
Format every day exactly like this:
`
# Day 1
- 60 mins: **Topic Name** - Brief description of the task.
- 30 mins: **Another Topic** - Brief description.

# Day 2
...
`
"""

class Task(BaseModel):
    name: str
    """Name of the task to be completed."""

    description: str
    """Description of the task to be completed. Should be between 10 and 20 words"""

    duration: int
    """Duration in minutes"""

class DailyPlan(BaseModel):
    day: int
    """Day number in the preparation plan."""

    tasks: list[Task]
    """List of tasks to be completed on this day."""


class CompletePlan(BaseModel):
    short_summary: str
    """A short 1 sentence executive summary."""

    # markdown_report: str
    # """The full markdown report."""

    daily_plans: list[DailyPlan]
    """A list of daily plans for the interview preparation."""





writer_agent = Agent(
    name="PlanWriterAgent",
    instructions=WRITER_PROMPT,
    model="gpt-5",
    tools=[]
)