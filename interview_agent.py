from openai import OpenAI
from agents import Agent, ModelSettings,Runner, WebSearchTool, function_tool, CodeInterpreterTool
import asyncio

client = OpenAI()


# prompt templat to fill by user

plannning_agent_instructions = """
# Role and Objective
You are an expert interview planning agent. Your task is to elaborate a roadmap for a user to prepare for a technical interview.

# Insructions
1. Read and understand the user's CV
2. Read and understant the job description provided by the user
3. Find weakenesses in the user's profile compared to the job description
4. Create a detailed daily plan to prepare for the interview, focusing on the weakenesses, on the required skills (hard and soft skills).
5. Suggest ressources (books, courses, articles, videos) for each topic in the plan, give exercices to practice.
"""

plannning_agent = Agent(
            name="Interview Planning Agent",
            model="gpt-5",
            instructions=plannning_agent_instructions,          
        )