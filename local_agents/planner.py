from pydantic import BaseModel

from agents import Agent


# PROMPT = """
# # Role and Objective
# You are an expert interview planning agent. Your task is to elaborate a roadmap for a user to prepare for a technical interview.

# # Instructions
# 1. Read and understand the user's CV.
# 2. Read and understand the job description.
# 3. Find weaknesses in the user's profile compared to the job description.
# 4. Create a daily plan to prepare for the interview.
# 5. Suggest resources and exercises.
# 6. Make the plan realistic and achievable.

# # Output
# A high-level preparation plan.
# """

PROMPT = """
    You are a job interview research planner designed to search any useful information to succeed. Given a request for preparing for a job interview, 
    produce a set of web searches to gather the context needed. Aim for job requirements, canditate weakeneses recent ressources, 
    trustworthy sources. 
    Output between 5 and 15 search terms to query for.
"""

class InterviewSearchItem(BaseModel):
    reason: str
    """Your reasoning for why this search is relevant."""

    query: str
    """The search term to feed into a web (or file) search."""

class InterviewSearchPlan(BaseModel):
    searches: list[InterviewSearchItem]
    """A list of search items to gather information for the interview plan."""

planning_agent = Agent(
    name="Interview Planning Agent",
    model="gpt-5",
    instructions=PROMPT,
    output_type=InterviewSearchPlan
)