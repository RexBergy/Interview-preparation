
import os
import webbrowser
import time
from datetime import datetime, timedelta

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from dateutil import parser as date_parser

from backend.local_agents.writer import CompletePlan

# When running locally, disable OAuthlib's HTTPs verification.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

calendar_service = None

def connect():
    """
    Starts the Google Calendar authentication flow.
    """
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['https://www.googleapis.com/auth/calendar.events.owned']
    )
    flow.redirect_uri = 'http://localhost:8080/oauth2callback'
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    return authorization_url

def fetch_token(url: str):
    """
    Fetches the Google Calendar token using the authorization URL.
    """
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['https://www.googleapis.com/auth/calendar.events.owned']
    )
    flow.redirect_uri = 'http://localhost:8080/oauth2callback'
    flow.fetch_token(authorization_response=url)
    return flow.credentials

async def oauth2callback(request):
    """
    Callback function for Google Calendar authentication.
    """
    global calendar_service
    auth_url = str(request.url)
    try:
        credentials = fetch_token(auth_url)
        calendar_service = build("calendar", "v3", credentials=credentials)
        return "Calendar authentication successful! You can close this tab."
    except Exception as e:
        return f"Error: {e}"

async def smart_schedule_quests(plan: CompletePlan, start_date: datetime, preferred_hour: int):
    """
    Scans the user's real calendar for free slots and schedules the Quests.
    """
    if not calendar_service:
        return "❌ Calendar not authenticated."

    # 1. Setup Time Boundaries
    try:
        cursor = start_date.astimezone()
    except:
        cursor = start_date # Fallback if timezone issues

    # Align to preferred hour
    if cursor.hour < preferred_hour:
        cursor = cursor.replace(hour=preferred_hour, minute=0, second=0)

    # Fetch busy slots (Batch)
    end_horizon = cursor + timedelta(days=len(plan.daily_plans) + 5)
    
    try:
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=cursor.isoformat(), 
            timeMax=end_horizon.isoformat(), 
            singleEvents=True, 
            orderBy='startTime'
        ).execute()
    except Exception as e:
        print(f"Failed to list calendar events: {e}")
        return f"⚠️ Error fetching calendar: {e}"
    
    busy_slots = []
    for e in events_result.get('items', []):
        if 'start' in e and 'dateTime' in e['start']:
            busy_slots.append(
                (
                    date_parser.parse(e['start']['dateTime']),
                    date_parser.parse(e['end']['dateTime'])
                )
            )

    # 2. Schedule Quests
    total_tasks = sum(len(d.tasks) for d in plan.daily_plans)
    tasks_done = 0

    for day in plan.daily_plans:
        # Start looking at the preferred hour of this calculated day
        day_target = cursor.replace(hour=preferred_hour, minute=0)
        if day_target < cursor: 
            day_target += timedelta(days=1)
        cursor = day_target

        for task in day.tasks:
            scheduled = False
            attempts = 0
            while not scheduled and attempts < 50: # Safety break
                attempts += 1
                proposed_end = cursor + timedelta(minutes=task.duration)
                
                # Check Overlaps
                conflict = False
                for (b_start, b_end) in busy_slots:
                    if (cursor < b_end) and (proposed_end > b_start):
                        conflict = True
                        cursor = b_end + timedelta(minutes=5) # Jump over conflict
                        break
                
                if not conflict:
                    # Insert
                    body = {
                        "summary": f"⚔️ Quest: {task.name}", # Gamified Title
                        "description": f"{task.description}\n\nXP Reward: {100 + task.duration//2}",
                        "start": {"dateTime": cursor.isoformat()},
                        "end": {"dateTime": proposed_end.isoformat()},
                    }
                    try:
                        calendar_service.events().insert(calendarId='primary', body=body).execute()
                        time.sleep(0.2) 
                    except Exception as e:
                        print(f"Calendar Insert Error: {e}")

                    cursor = proposed_end + timedelta(minutes=10) # Break
                    scheduled = True
                    tasks_done += 1
    
    return "✅ All quests synced to Calendar!"
