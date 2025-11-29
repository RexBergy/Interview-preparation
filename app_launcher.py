import gradio as gr
import uvicorn
from backend.game_agent import app
from gradio_frontend.game_ui_gradio import demo

# Mount the Gradio app to the FastAPI app
gr.mount_gradio_app(app, demo, path="/")

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080)
