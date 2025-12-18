# main.py

"""
Main entry point for the Interview Quest FastAPI application.

This file initializes the FastAPI app, mounts the frontend static files,
defines the root endpoint to serve the main HTML page, and includes
the API routers for different functionalities like game logic and calendar integration.
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import game_router, calendar_router

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


app.include_router(game_router.router, prefix="/api", tags=["Game"])
app.include_router(calendar_router.router, prefix="/api", tags=["Calendar"])

if __name__ == "__main__":
    import uvicorn

 
    uvicorn.run(app, host="localhost", port=8080)
