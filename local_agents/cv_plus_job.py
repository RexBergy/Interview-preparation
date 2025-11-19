from pydantic import BaseModel

from agents import Agent


PROMPT = """
    You are a cv reader. Given a cv find the users strengths and weaknesses for a job interview
    based on the job description provided. Focus on technical skills, soft skills (Communication: Effectively listening, speaking, and writing to convey information.
Teamwork: Collaborating with others to achieve common goals.
Problem-solving: Using critical thinking and creativity to find solutions.
Adaptability: Adjusting to new situations, processes, and challenges.
Emotional Intelligence: Understanding and managing your own emotions and recognizing those of others.
Time Management: Organizing and prioritizing tasks to meet deadlines.
Leadership: Inspiring and guiding a team or project.
Work Ethic: Demonstrating professionalism, dependability, and a strong sense of responsibility.
Critical Thinking:) and experience.
    Try to read between the lines and find gaps that are not explicitly mentionned.
"""

class CandidateProfile(BaseModel):
    strengths: list[str]
    """List of strengths based on the CV and job description."""

    weaknesses: list[str]
    """List of weaknesses based on the CV and job description."""

    technical_skills_gap: list[str]
    """List of technical skills that need improvement."""

    soft_skills_gap: list[str]
    """List of soft skills that need improvement."""



cv_job_reader = Agent(
    name="CV Reader Agent",
    model="gpt-5",
    instructions=PROMPT,
    output_type=CandidateProfile
)