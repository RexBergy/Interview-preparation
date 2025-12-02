# backend/calendar_utils.py

"""
Utilities for interacting with the Google Calendar API.

This module handles the entire OAuth2 flow for Google Calendar, including:
- Generating the authentication URL.
- Handling the OAuth2 callback to obtain user credentials.
- Providing a configured Google Calendar API service instance.
- Intelligently scheduling study quests into free slots on the user's calendar.
"""

import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build, Resource
from dateutil import parser as date_parser
from fastapi import Request

from backend.plan_parser import CompletePlan

# --- Configuration ---

# This environment variable is used for local development to bypass the HTTPS requirement.
# It should NOT be set in a production environment.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# The path to the client secrets file obtained from the Google API Console.
CLIENT_SECRETS_FILE = 'client_secret.json'

# The scopes define the level of access the application is requesting.
# This scope allows creating and managing events in the user's calendars.
SCOPES = ['https://www.googleapis.com/auth/calendar.events.owned']

# The redirect URI must match one of the authorized redirect URIs in the Google API Console.
REDIRECT_URI = 'http://localhost:8080/api/oauth2callback'

# A global variable to hold the initialized Google Calendar service instance.
calendar_service: Resource | None = None

# --- OAuth2 and Service Management ---

def get_calendar_connect_url() -> str:
    """
    Generates the Google OAuth2 authentication URL.

    This URL directs the user to Google's consent screen to grant the application
    permission to access their calendar.

    Returns:
        The authorization URL to which the user should be redirected.
    """
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    return authorization_url

async def handle_calendar_oauth_callback(request: Request):
    """
    Handles the OAuth2 callback from Google after user authorization.

    It exchanges the authorization code for credentials, builds the Google
    Calendar service, and stores it in the global `calendar_service` variable.

    Args:
        request: The incoming FastAPI request containing the full callback URL.
    """
    print("Handling calendar OAuth2 callback...")
    global calendar_service
    # Reconstruct the full URL from the request for the flow.
    auth_url = str(request.url)
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=request.query_params.get("state")
    )
    flow.redirect_uri = REDIRECT_URI

    # Exchange the authorization code for credentials.
    flow.fetch_token(authorization_response=auth_url)
    credentials = flow.credentials

    # Build and store the calendar service resource.
    calendar_service = build("calendar", "v3", credentials=credentials)
    print("Calendar service built successfully.")
    print("Calendar sefice:",calendar_service)


# --- Quest Scheduling Logic ---

async def smart_schedule_quests(
    plan: CompletePlan, start_date: date, preferred_hour: int
):
    """
    Schedules all quests from the study plan into available slots in the user's
    primary Google Calendar.

    This function fetches busy time slots from the user's calendar and then
    iteratively finds the next available slot for each quest, starting from the
    user's preferred study time.

    Args:
        plan: The structured study plan containing daily quests.
        start_date: The date to start scheduling from.
        preferred_hour: The user's preferred hour of the day to study (0-23).

    Raises:
        ConnectionError: If the calendar service has not been authenticated.
        Exception: If there is an error fetching calendar events or inserting new ones.
    """
    if not calendar_service:
        raise ConnectionError("Google Calendar service not authenticated.")

    # 1. Define time boundaries and fetch existing busy slots.
    scheduling_start_dt = datetime.combine(start_date, datetime.min.time()).astimezone()
    scheduling_end_dt = scheduling_start_dt + timedelta(days=len(plan.daily_plans) + 14) # Look ahead buffer
    
    busy_slots = _get_busy_slots(scheduling_start_dt, scheduling_end_dt)

    # 2. Iterate through the plan and schedule each task.
    cursor = scheduling_start_dt
    for day_plan in plan.daily_plans:
        # Align the cursor to the preferred study hour for the current day.
        day_target_dt = cursor.replace(hour=preferred_hour, minute=0, second=0, microsecond=0)
        if day_target_dt < cursor:
            day_target_dt += timedelta(days=1)
        cursor = day_target_dt
        
        for task in day_plan.tasks:
            # Find the next free slot and create the event.
            slot_start, slot_end = _find_next_available_slot(cursor, task.duration, busy_slots)
            _create_calendar_event(task, slot_start, slot_end)
            
            # Add the newly created event to our list of busy slots to avoid overlap.
            busy_slots.append((slot_start, slot_end))
            busy_slots.sort() # Keep the list sorted for efficient searching.

            # Move the cursor to the end of the newly scheduled event for the next search.
            cursor = slot_end + timedelta(minutes=10) # Add a small buffer

def _get_busy_slots(start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
    """Fetches all busy time slots from the primary calendar within a given timeframe."""
    try:
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        # Return an empty list or raise an exception, depending on desired error handling.
        return []

    busy_slots = []
    for event in events_result.get('items', []):
        # We only care about events with a specific start and end time.
        if 'dateTime' in event['start'] and 'dateTime' in event['end']:
            start_dt = date_parser.isoparse(event['start']['dateTime'])
            end_dt = date_parser.isoparse(event['end']['dateTime'])
            busy_slots.append((start_dt, end_dt))
    return busy_slots

def _find_next_available_slot(
    search_start_dt: datetime, duration_minutes: int, busy_slots: List[Tuple[datetime, datetime]]
) -> Tuple[datetime, datetime]:
    """Finds the next available time slot of a given duration."""
    proposed_start = search_start_dt
    
    while True:
        proposed_end = proposed_start + timedelta(minutes=duration_minutes)
        is_conflict = False
        for busy_start, busy_end in busy_slots:
            # Check for overlap: (StartA < EndB) and (EndA > StartB)
            if proposed_start < busy_end and proposed_end > busy_start:
                # Conflict found, jump the proposed start to the end of the conflicting event.
                proposed_start = busy_end + timedelta(minutes=1) # Add 1 minute buffer
                is_conflict = True
                break # Restart the check with the new proposed_start
        
        if not is_conflict:
            # No conflicts found, this is a valid slot.
            return proposed_start, proposed_end

def _create_calendar_event(task: Any, start_dt: datetime, end_dt: datetime):
    """Creates a new event in the primary Google Calendar."""
    event_body = {
        "summary": f"⚔️ Quest: {task.name}",
        "description": f"{task.description}",
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }
    try:
        calendar_service.events().insert(calendarId='primary', body=event_body).execute()
    except Exception as e:
        # In a real app, you might want a more robust retry or logging mechanism.
        print(f"Failed to insert calendar event for task '{task.name}': {e}")


def request_calendar_service() -> Resource | None:
    """Returns the global calendar service instance."""
    global calendar_service
    return calendar_service
    
