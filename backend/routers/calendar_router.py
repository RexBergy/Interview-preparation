# backend/routers/calendar_router.py

"""
API router for handling Google Calendar integration.

This router provides endpoints for initiating the OAuth2 flow to connect a user's
Google Calendar and for handling the callback after the user grants permission.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from backend.calendar_utils import get_calendar_connect_url, handle_calendar_oauth_callback

# Create an API router for calendar-related endpoints.
router = APIRouter()


@router.get("/connect_calendar", summary="Get Google Calendar Authentication URL")
def connect_calendar():
    """
    Generates and returns the authentication URL for Google Calendar.

    This URL is used to redirect the user to Google's consent screen to
    authorize the application to access their calendar.

    Returns:
        dict: A dictionary containing the `auth_url` for the user to visit.
    """
    auth_url = get_calendar_connect_url()
    print(f"Generated auth URL: {auth_url}")
    return {"auth_url": auth_url}


@router.get("/oauth2callback", summary="Handle Google Calendar OAuth2 Callback")
async def handle_oauth2callback(request: Request):
    """
    Handles the OAuth2 callback from Google after the user has authorized the application.

    This endpoint receives the authorization code from Google, exchanges it for an
    access token, and stores the credentials for future use.

    Args:
        request (Request): The incoming request object from FastAPI, containing the
                         full URL with the authorization code.

    Returns:
        HTMLResponse: A simple HTML page to notify the user of success and
                      instruct them to close the tab.
    """
    print("Received OAuth2 callback")
    await handle_calendar_oauth_callback(request)

    return HTMLResponse(
        content="""
        <html>
            <head><title>Authentication Successful</title></head>
            <body>
                <h1>Authentication successful!</h1>
                <p>You can now close this tab and return to the application.</p>
            </body>
        </html>
    """
    )