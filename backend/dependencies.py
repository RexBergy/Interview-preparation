# backend/dependencies.py

"""
Manages shared dependencies for the FastAPI application.

This file is used to create and provide singleton instances of classes
that need to be shared across different parts of the application,
such as the GameManager which holds the main game state.

FastAPI's dependency injection system will use the functions defined here
to pass these shared instances to the API route handlers.
"""

from backend.game_manager import GameManager

# Create a single, shared instance of the GameManager.
# This instance will persist across multiple API requests, holding the game state.
game_manager = GameManager()

def get_game_manager() -> GameManager:
    """
    FastAPI dependency to get the shared GameManager instance.

    Returns:
        The singleton GameManager instance.
    """
    return game_manager

