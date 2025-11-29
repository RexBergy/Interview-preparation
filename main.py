# main.py

"""
Main entry point for the Interview Quest FastAPI application.

This file initializes the FastAPI app, mounts the frontend static files,
defines the root endpoint to serve the main HTML page, and includes
the API routers for different functionalities like game logic and calendar integration.
"""

import os
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.dependencies import get_game_manager
from backend.routers import game_router, calendar_router
from backend.game_manager import GameManager

# When running locally, disable OAuthlib's HTTPS verification for development purposes.
# This should not be used in a production environment.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Initialize the FastAPI application.
app = FastAPI(
    title="Interview Quest API",
    description="A gamified interview preparation tool.",
    version="1.0.0"
)

# Mount the 'frontend' directory to serve static files like CSS and JavaScript.
# This allows the HTML file to link to these assets.
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serves the main `index.html` file as the root of the application.

    Returns:
        HTMLResponse: The content of the `index.html` file.
    """
    with open("frontend/index.html") as f:
        return HTMLResponse(content=f.read())


# Include the API routers that define the application's endpoints.
app.include_router(game_router.router, prefix="/api", tags=["Game"])
app.include_router(calendar_router.router, prefix="/api", tags=["Calendar"])

# The following block allows running the app directly with uvicorn for development.
if __name__ == "__main__":
    import uvicorn

    # Note: In a production deployment, you would typically use a production-grade
    # ASGI server like Gunicorn with Uvicorn workers.
    uvicorn.run(app, host="localhost", port=8080)
