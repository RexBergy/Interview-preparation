
import random
from typing import List, Dict
import pandas as pd

from local_agents.writer import CompletePlan

def init_game_state(plan: CompletePlan) -> List[Dict]:
    """Transforms the static 'CompletePlan' into an interactive 'Game State'."""
    game_tasks = []
    task_id = 0
    difficulties = ["Normal", "Hard", "Hardest"]
    
    for day in plan.daily_plans:
        for task in day.tasks:
            is_boss = "mock" in task.name.lower()
            difficulty = "Hardest" if is_boss else random.choice(difficulties)
            
            # XP Calculation
            base_xp = {"Normal": 50, "Hard": 100, "Hardest": 150}[difficulty]
            duration_xp = task.duration // 2
            xp = base_xp + duration_xp
            if is_boss:
                xp *= 1.5  # 50% multiplier for bosses

            game_tasks.append({
                "id": task_id,
                "day": f"Day {day.day}",
                "name": task.name,
                "desc": task.description,
                "status": "🔓 UNLOCKED" if task_id == 0 else "🔒 LOCKED", 
                "xp_reward": int(xp), 
                "type": "BOSS BATTLE" if is_boss else "QUEST",
                "difficulty": difficulty
            })
            task_id += 1
            
    return game_tasks

def render_quest_board(game_tasks: List[Dict]) -> pd.DataFrame:
    """Converts game state into a clean DataFrame for the UI."""
    data = []
    if not game_tasks:
        return pd.DataFrame(columns=["Status", "Timeline", "Quest Objective", "Rewards"])

    for t in game_tasks:
        status_icon = t['status']
        if t['status'] == "COMPLETED":
            status_icon = "✅ DONE"
        
        name = t['name']
        if t['type'] == "BOSS BATTLE":
            name = f"💀 {name.upper()}"

        data.append([
            status_icon,
            t['day'],
            name,
            f"+{t['xp_reward']} XP"
        ])
    
    return pd.DataFrame(
        data, 
        columns=["Status", "Timeline", "Quest Objective", "Rewards"]
    )

def calculate_player_stats(game_tasks: List[Dict]):
    """Calculates total XP and Level."""
    if not game_tasks:
        return 0, 1, "Novice"
        
    current_xp = sum(t['xp_reward'] for t in game_tasks if t['status'] == "COMPLETED")
    level = 1 + (current_xp // 500)
    titles = ["Novice", "Apprentice", "Journeyman", "Expert", "Master", "Grandmaster"]
    title = titles[min(level-1, len(titles)-1)]
    return current_xp, level, title
