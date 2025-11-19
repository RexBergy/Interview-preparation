from pydantic import BaseModel

from agents import Agent, WebSearchTool

# Writer agent brings together the raw search results and optionally calls out
# to sub‑analyst tools for specialized commentary, then returns a cohesive markdown report.
WRITER_PROMPT = """
You are an expert interview preparation plan writer. Your task is to create a comprehensive, extensive,
detailed plan to prepare a candidate for an upcoming job interviewbased on the search results provided,
the candidate profile, and any additional candidate information. 

# Instructions
1. Find how many days are available for preparation based on the candidate information.
2. Find how many total hours are available for preparation based on this.
3. Create a daily plan that breaks down the preparation into manageable tasks
4. Make sure to cover all material found in the search results and address all weaknesses found in the candidate profile
5. The task descriptions should be extensive and detailed, between 50 and 200 words. They should include sources for further reading.
6. Check the user's calendar with the check_schedule tool
7. Create events to the users calendar with the create_event tool
"""

class Task(BaseModel):
    name: str
    """Name of the task to be completed."""

    description: str
    """Description of the task to be completed. Should be between 50 and 200 words"""

class DailyPlan(BaseModel):
    day: int
    """Day number in the preparation plan."""

    tasks: list[Task]
    """List of tasks to be completed on this day."""


class CompletePlan(BaseModel):
    short_summary: str
    """A short 2-3 sentence executive summary."""

    # markdown_report: str
    # """The full markdown report."""

    daily_plans: list[DailyPlan]
    """A list of daily plans for the interview preparation."""





writer_agent = Agent(
    name="PlanWriterAgent",
    instructions=WRITER_PROMPT,
    model="gpt-5",
    tools=[WebSearchTool()],
    output_type=CompletePlan,
)