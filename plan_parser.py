
import re
from local_agents.writer import CompletePlan, DailyPlan, Task

def parse_markdown_to_plan(markdown_text: str) -> CompletePlan:
    """Parses the Agent's markdown output into a structured Plan object."""
    lines = markdown_text.split('\n')
    daily_plans = []
    current_day = 0
    current_tasks = []
    summary = "Your custom strategy."

    # Matches: "- 60 mins: **Title** - Description"
    # Added flexibility for spaces/formatting
    task_pattern = re.compile(r'-\s+(\d+)\s*mins?:\s*\*\*(.*?)\*\*\s*-\s*(.*)')
    
    for line in lines:
        line = line.strip()
        
        # Day Header
        day_match = re.search(r'Day\s+(\d+)', line, re.IGNORECASE)
        if day_match and line.startswith('#'):
            if current_day > 0 and current_tasks:
                daily_plans.append(DailyPlan(day=current_day, tasks=current_tasks))
            current_day = int(day_match.group(1))
            current_tasks = []
            continue

        # Task Item
        match = task_pattern.match(line)
        if match:
            current_tasks.append(Task(
                duration=int(match.group(1)),
                name=match.group(2).strip(),
                description=match.group(3).strip()
            ))

    if current_day > 0 and current_tasks:
        daily_plans.append(DailyPlan(day=current_day, tasks=current_tasks))

    return CompletePlan(short_summary=summary, daily_plans=daily_plans)
