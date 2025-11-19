from agents import Agent
from pydantic import BaseModel

PROMPT = """
You are an expert interview preparation progress judge. Your task is to evaluate the feasibility and progression of a proposed interrview preparation
plan based on the candidate profile, job description, and available time."""

class Advice(BaseModel):
    summary: str
    """A brief summary of the feasibility analysis and suggested improvements."""

feasibility_agent = Agent(
    name="Feasibility Agent",
    model="gpt-5-nano",
    instructions=PROMPT,
    output_type=Advice
)
