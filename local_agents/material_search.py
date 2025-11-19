from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

# Given a search term, use web search to pull back a brief summary.
# Summaries should be concise but capture the main points.
INSTRUCTIONS = (
    "You are a research assistant specializing in everything related to job interviews. "
    "Given a search term, use web search to retrieve up-to-date context and "
    "produce a short summary of at most 300 words. Include source. Focus on key concepts, facts, "
    "or explanations that will be useful to an interview canditate."
)

search_agent = Agent(
    name="InterviewSearchAgent",
    model="gpt-4.1",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool()],
    model_settings=ModelSettings(tool_choice="required"),
)