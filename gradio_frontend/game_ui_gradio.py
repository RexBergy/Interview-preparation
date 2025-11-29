from __future__ import annotations

import gradio as gr
from gradio.themes.base import Base

# Import game logic functions that the UI will call
from backend.game_agent import (
    stream_plan_generation,
    on_quest_click,
    start_quiz,
    get_help,
    back_to_board,
    submit_quiz_answers
)


# ============================================================
# 🖥️ UI LAYOUT
# ============================================================

class MedievalFantasy(Base):
    def __init__(self):
        super().__init__(
            primary_hue=gr.themes.colors.slate, # Black/dark gray base
            secondary_hue=gr.themes.colors.gray, # Silver/light gray accents
            neutral_hue=gr.themes.colors.gray,
            font=(
                gr.themes.GoogleFont("Lora"),
                "ui-serif",
                "Georgia",
                "serif",
            ),
        )
        self.set(
            # Colors -- Black & Silver Theme
            body_background_fill="#0d0d0d",
            body_background_fill_dark="#0d0d0d",
            body_text_color="#e0e0e0", # Light silver text
            body_text_color_dark="#e0e0e0",

            button_primary_background_fill="#b0b0b0", # Silver
            button_primary_background_fill_dark="#b0b0b0",
            button_primary_text_color="#000000", # Black text on silver button
            
            button_secondary_background_fill="#333333", # Dark silver/charcoal
            button_secondary_background_fill_dark="#333333",
            button_secondary_text_color="#e0e0e0", # Light silver text

            # Component Styling
            block_background_fill="#1a1a1a", # Near-black
            block_border_width="1px",
            block_border_color="#333333", # Dark silver border
            block_title_text_color="#e0e0e0",

            input_background_fill="#333333",
            input_border_color="#555555",
            
            # Slider
            slider_color="#b0b0b0", # Silver
            slider_color_dark="#b0b0b0",
        )
css = """
.container { max-width: 900px; margin: auto; } 
.feedback { font-weight: bold; font-size: 1.1em; }
@keyframes progress-bar-stripes {
  from { background-position: 40px 0; }
  to { background-position: 0 0; }
}
"""

with gr.Blocks(title="Career Quest", theme=MedievalFantasy(), css=css) as demo:
    
    # Global State
    game_state_store = gr.State([]) 
    active_task_idx = gr.State(-1)
    active_quiz_data = gr.State([])
    player_lives = gr.State(3)
    quest_failed = gr.State(False)

    gr.Markdown("# Career Quest: Gamified Prep", elem_classes="text-center")

    # --- STEP 1: SETUP ---
    with gr.Column(visible=True) as step_1_col:
        gr.Markdown("### 👤 Character Setup")
        with gr.Row():
            role_input = gr.Textbox(label="Target Role (Class)", placeholder="e.g. Nurse, Python Dev")
            hours_input = gr.Slider(1, 10, value=2, label="Hours per Day")
        
        goal_input = gr.Textbox(label="Main Quest Goal", placeholder="e.g. Land a senior role")
        job_description_input = gr.Textbox(label="Job Description (Optional)", placeholder="Paste the job description here to tailor your quests.")
        
        with gr.Row():
            start_date = gr.DateTime(label="Start Date")
            interview_date = gr.DateTime(label="Boss Battle Date")

        with gr.Row():
            use_cal = gr.Checkbox(label="📅 Sync Quests to Google Calendar")
            pref_time = gr.Dropdown(choices=[("Morning (9AM)", 9), ("Afternoon (2PM)", 14), ("Evening (6PM)", 18)], value=18, label="Quest Time")

        generate_btn = gr.Button("⚔️ Generate Campaign", variant="primary")

    # --- STEP 2: GAME BOARD ---
    with gr.Column(visible=False) as step_2_col:
        loading_msg = gr.Markdown("### 🧙‍♂️ The Oracle is crafting your destiny...", visible=False)
        raw_stream_output = gr.Markdown(visible=False)

        # Container for the main board (Hidden when quiz is open)
        with gr.Group(visible=False) as board_container:
            stats_display = gr.HTML()
            gr.Markdown("### 📜 Quest Board")
            
            with gr.Column(visible=True) as quest_board_col:
                quest_board = gr.Dataset(
                    components=["textbox", "textbox", "textbox", "textbox"],
                    headers=["Status", "Timeline", "Quest Objective", "Rewards"],
                )
                board_feedback = gr.Textbox(label="System Log", interactive=False)

            with gr.Column(visible=False) as quest_details_col:
                gr.Markdown("### ⚔️ Quest Details")
                quest_details_md = gr.Markdown("No quest selected.")
                with gr.Row():
                    start_quiz_btn = gr.Button("🧠 Start Quiz", variant="primary")
                    get_help_btn = gr.Button("📚 Get Help")
                back_to_board_btn = gr.Button("⬅️ Back to Quest Board")


        # Container for the Quiz Overlay (Hidden by default)
        with gr.Group(visible=False) as quiz_modal:
            gr.Markdown("## 🧠 Knowledge Check")
            q_header = gr.Markdown("Loading...")
            quiz_loading_msg = gr.Markdown("### 🧙‍♂️ Forging your questions...", visible=False)
            with gr.Group(visible=True) as quiz_questions_group:
                q1_comp = gr.Radio(label="Q1")
                q2_comp = gr.Radio(label="Q2")
                q3_comp = gr.Radio(label="Q3")
                q4_comp = gr.Radio(label="Q4", visible=False)
                q5_comp = gr.Radio(label="Q5", visible=False)
                q6_comp = gr.Radio(label="Q6", visible=False)
                submit_quiz_btn = gr.Button("Submit Answers", variant="primary")
            feedback_box = gr.Markdown(elem_classes="feedback")


    # --- WIRING ---
    generate_btn.click(
        fn=stream_plan_generation,
        inputs=[role_input, goal_input, job_description_input, hours_input, start_date, interview_date, use_cal, pref_time],
        outputs=[raw_stream_output, step_1_col, step_2_col, game_state_store, quest_board, stats_display, loading_msg, board_container]
    )

    quest_board.select(
        fn=on_quest_click,
        inputs=[game_state_store, quest_failed],
        outputs=[quest_board_col, quest_details_col, quest_details_md, active_task_idx, board_feedback, quest_failed]
    )
    
    start_quiz_btn.click(
        fn=start_quiz,
        inputs=[active_task_idx, game_state_store, role_input],
        outputs=[
            quest_details_col, quiz_modal, active_quiz_data, q_header, feedback_box, 
            q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp,
            quiz_loading_msg, quiz_questions_group, player_lives, quest_failed
        ]
    )

    get_help_btn.click(
        fn=get_help,
        inputs=[active_task_idx, game_state_store],
        outputs=[quest_details_md]
    )

    back_to_board_btn.click(
        fn=back_to_board,
        inputs=[],
        outputs=[quest_board_col, quest_details_col, quiz_modal]
    )

    submit_quiz_btn.click(
        fn=submit_quiz_answers,
        inputs=[active_task_idx, q1_comp, q2_comp, q3_comp, q4_comp, q5_comp, q6_comp, active_quiz_data, game_state_store, player_lives],
        outputs=[feedback_box, quest_board_col, quest_details_col, quiz_modal, game_state_store, quest_board, stats_display, board_feedback, player_lives, quest_failed]
    )
