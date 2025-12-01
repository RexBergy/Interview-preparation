// frontend/ui.js

/**
 * @file Manages all DOM manipulations, UI updates, and visual interactions for the Interview Quest application.
 * This module centralizes control over the user interface, from populating forms to rendering dynamic content like game boards and modals.
 */

import { getGameState } from './api.js';

// --- DOM Element References ---

/**
 * A centralized object containing references to all key DOM elements.
 * This improves performance by avoiding repeated DOM queries and makes code more readable.
 * @const
 */
export const DOM = {
  introSection: document.querySelector('.intro-section'),
  setupStep: document.getElementById('setup-step'),
  loadingStep: document.getElementById('loading-step'),
  gameBoardStep: document.getElementById('game-board-step'),
  setupForm: document.getElementById('setup-form'),
  formPages: document.querySelectorAll('.form-page'),
  nextBtn: document.getElementById('next-btn'),
  prevBtn: document.getElementById('prev-btn'),
  calYesBtn: document.getElementById('cal-yes-btn'),
  calNoBtn: document.getElementById('cal-no-btn'),
  generatePlanBtn: document.getElementById('generate-plan-btn'),
  planStreamEl: document.getElementById('plan-stream'),
  loadingStatusEl: document.getElementById('loading-status'),
  questBoardBody: document.querySelector('#quest-board-table tbody'),
  playerStatsEl: document.getElementById('player-stats'),
  quizModal: document.getElementById('quiz-modal'),
  quizForm: document.getElementById('quiz-form'),
  quizTitle: document.getElementById('quiz-title'),
  quizQuestionsContainer: document.getElementById('quiz-questions-container'),
  quizResultEl: document.getElementById('quiz-result'),
  quizLoading: document.getElementById('quiz-loading'),
  closeQuizBtn: document.getElementById('close-quiz-btn'),
  gameOverModal: document.getElementById('game-over-modal'),
  restartGameBtn: document.getElementById('restart-game-btn'),
  trainingModal: document.getElementById('training-modal'),
  trainingTitle: document.getElementById('training-title'),
  trainingContent: document.getElementById('training-content'),
  closeTrainingBtn: document.getElementById('close-training-btn'),
};

/**
 * Initializes date input fields to sensible defaults.
 * It sets the minimum selectable date to today to prevent users from choosing past dates
 * and defaults the start date to today.
 */
export function setMinDates() {
  const today = new Date().toISOString().split('T')[0];
  const startDateInput = document.getElementById('start_date');
  const interviewDateInput = document.getElementById('interview_date');
  
  startDateInput.setAttribute('min', today);
  startDateInput.value = today;
  interviewDateInput.setAttribute('min', today);
}

/**
 * Populates the 'Preferred Study Hour' dropdown with a range of time options (7 AM to 9 PM).
 * It also pre-selects a default time (9 AM).
 */
export function populateTimeSelect() {
  const select = document.getElementById('pref_time');
  const times = {
    "Morning (7am-11am)": "9",
    "Afternoon (12pm-5pm)": "13",
    "Evening (6pm-9pm)": "18",
    "Night (9pm-11pm)": "21"
  };

  for (const [text, value] of Object.entries(times)) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = text;
    if (value === "9") option.selected = true;
    select.appendChild(option);
  }
}

/**
 * Populates the 'Hours/Day' dropdown with a variety of study duration options,
 * ranging from 15 minutes to 8 hours. It pre-selects a default of 2 hours.
 */
export function populateHoursSelect() {
    const select = document.getElementById('hours');
    const values = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3, 4, 5, 6, 8];

    values.forEach(value => {
        const option = document.createElement('option');
        option.value = value;

        let text = '';
        if (value < 1) {
            text = `${value * 60} min`;
        } else {
            const hours = Math.floor(value);
            const minutes = (value % 1) * 60;
            text = `${hours}h`;
            if (minutes > 0) {
                text += ` ${minutes} min`;
            }
        }
        option.textContent = text;

        if (value === 2) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

/**
 * Manages the visibility of the main application steps (views).
 * It shows the specified step and ensures all others are hidden.
 * @param {'setup' | 'loading' | 'game-board'} stepToShow - The ID suffix of the step to display.
 */
export function showStep(stepToShow) {
  const steps = {
    setup: DOM.setupStep,
    loading: DOM.loadingStep,
    'game-board': DOM.gameBoardStep,
  };

  // Hide intro section if not on the setup step
  if (stepToShow !== 'setup') {
    DOM.introSection.classList.add('hidden');
  } else {
    DOM.introSection.classList.remove('hidden');
  }

  for (const stepName in steps) {
    const stepElement = steps[stepName];
    const isVisible = stepName === stepToShow;
    
    if (isVisible) {
      stepElement.classList.remove('hidden');
      // Set up and trigger animation for the appearing step
      stepElement.classList.add('fade-in-slide-up');
      // Use a timeout to ensure the transition is applied correctly
      setTimeout(() => stepElement.classList.add('visible'), 50);
    } else {
      stepElement.classList.add('hidden');
      stepElement.classList.remove('visible', 'fade-in-slide-up');
    }
  }
}

/**
 * Appends new content to the plan generation stream element and auto-scrolls to the bottom.
 * @param {string} newContent - The new text content to append.
 */
export function updatePlanStream(newContent) {
    DOM.planStreamEl.textContent += newContent;
    DOM.planStreamEl.scrollTop = DOM.planStreamEl.scrollHeight;
}

/**
 * Updates the loading status message displayed to the user during long operations.
 * @param {string} statusText - The new status message to display.
 */
export function updateLoadingStatus(statusText) {
    DOM.loadingStatusEl.textContent = statusText;
}

/**
 * Asynchronously fetches the latest game state and triggers the rendering
 * of both the player stats and the quest board.
 */
export async function loadAndRenderGameBoard() {
    try {
        const state = await getGameState();
        renderPlayerStats(state.stats);
        renderQuestBoard(state.board);
        return state; // Return the entire state object
    } catch (error) {
        console.error(error);
        alert(error.message); // Inform the user of the failure.
        return null; // Return null on error
    }
}

/**
 * Renders the player's statistics section, including level, title, XP, and lives.
 * @param {object} stats - The player's stats object from the game state.
 * @property {number} stats.level - The player's current level.
 * @property {string} stats.title - The player's current title (e.g., "Novice").
 * @property {number} stats.xp_in_level - XP earned within the current level.
 * @property {number} stats.xp_per_level - Total XP required for the current level.
 * @property {number} stats.lives - Remaining lives.
 * @property {number} stats.xp - Total accumulated XP.
 */
function renderPlayerStats(stats) {
    const progressPercent = stats.xp_per_level > 0 ? (stats.xp_in_level / stats.xp_per_level) * 100 : 0;
    DOM.playerStatsEl.innerHTML = `
        <div class="intro-text">
            <h2>Welcome to your Quest Board!</h2>
            <p>Embark on your personalized journey to interview mastery. Conquer quests to gain XP, level up, and ultimately, ace your interview. Locked quests will become available as you progress. The timeline provided is a flexible guide based on your goals. Train your skills, and when you feel ready, enter the battle. You have three lives for each battle, make them count. Good luck, adventurer!</p>
        </div>
        <h3>Level ${stats.level} ${stats.title}</h3>
        <div class="progress-bar-container">
            <div class="progress-bar" style="width: ${progressPercent}%"></div>
            <div class="progress-bar-text">${stats.xp_in_level} / ${stats.xp_per_level} XP</div>
        </div>
        <p>Total XP: ✨ ${stats.xp}</p>
    `;
}

/**
 * Renders the main quest board table from the game state data.
 * @param {Array<object>} board - An array of task objects representing the quests.
 */
function renderQuestBoard(board) {
    DOM.questBoardBody.innerHTML = ''; // Clear existing board
    board.forEach((task, index) => {
        const row = document.createElement('tr');
        row.classList.add('fade-in-slide-up'); // Prepare for animation

        const isClickable = task.Status !== '🔒 LOCKED' && task.Status !== '✅ DONE';
        row.innerHTML = `
            <td>${task.Status}</td>
            <td>${task.Timeline}</td>
            <td>${task['Quest Objective']}</td>
            <td>${task.Rewards}</td>
            <td>
                <button class="train-btn" data-quest="${task['Quest Objective']}" title="Train">
                    📖
                </button>
            </td>
            <td>
                <button data-index="${index}" data-status="${task.Status}" ${!isClickable ? 'disabled' : ''}>
                    ${task.Status === '✅ DONE' ? 'Completed' : 'start'}
                </button>
            </td>
        `;
        DOM.questBoardBody.appendChild(row);

        // Stagger the animation for each row
        setTimeout(() => {
            row.classList.add('visible');
        }, index * 100);
    });
}

/**
 * Shows or hides the loading spinner within the quiz modal.
 * @param {boolean} isLoading - If true, shows loading state; otherwise, shows the form.
 */
export function showQuizLoading(isLoading) {
    DOM.quizLoading.classList.toggle('hidden', !isLoading);
    DOM.quizForm.classList.toggle('hidden', isLoading);
    DOM.quizTitle.classList.toggle('hidden', isLoading);
}

/**
 * Opens and populates the quiz modal with questions for the selected quest.
 * @param {object} quizData - The data for the quiz.
 * @param {string} quizData.task_name - The name of the current quest/task.
 * @param {Array<object>} quizData.questions - An array of question objects.
 */
export function openQuizModal(quizData) {
    showQuizLoading(true);
    DOM.quizModal.classList.remove('hidden');
    document.body.classList.add('modal-open');

    if (quizData) {
        DOM.quizTitle.textContent = `⚔️ Quest: ${quizData.task_name}`;
        DOM.quizQuestionsContainer.innerHTML = ''; // Clear previous questions
        quizData.questions.forEach((q, i) => {
            const questionDiv = document.createElement('div');
            questionDiv.className = 'quiz-question';
            const optionsHtml = q.options.map((opt) => `
                <label>
                    <input type="radio" name="q${i}" value="${opt}" required>
                    ${opt}
                </label>
            `).join('');
            questionDiv.innerHTML = `
                <p>${i + 1}. ${q.q}</p>
                <div class="quiz-options">${optionsHtml}</div>
            `;
            DOM.quizQuestionsContainer.appendChild(questionDiv);
        });
        showQuizLoading(false);
    }



    // Reset modal state
    DOM.quizResultEl.classList.add('hidden');
    DOM.closeQuizBtn.classList.add('hidden');
}

/**
 * Closes the quiz modal and restores background scrolling.
 */
export function closeQuizModal() {
    DOM.quizModal.classList.add('hidden');
    document.body.classList.remove('modal-open');
}

/**
 * Displays the final result of the submitted quiz.
 * Handles UI changes for pass, fail, and game-over scenarios.
 * @param {object} result - The quiz result data from the server.
 * @param {boolean} result.passed - Whether the user passed the quiz.
 * @param {number} result.score - The number of correct answers.
 * @param {number} result.total - The total number of questions.
 * @param {boolean} [result.game_over] - Optional flag indicating if the game is over.
 * @param {number} [result.lives_left] - Optional count of remaining lives.
 */
export function displayQuizResult(result) {
    DOM.quizForm.classList.add('hidden');
    DOM.quizResultEl.classList.remove('hidden');
    DOM.closeQuizBtn.classList.remove('hidden');

    let message = '';
    if (result.passed) {
        DOM.quizResultEl.className = 'result-success';
        message = `<h3>🎉 Victory! Quest Complete! 🎉</h3>
                   <p>Score: ${result.score}/${result.total}</p>`;
    } else {
        DOM.quizResultEl.className = 'result-fail';
        if (result.game_over) {
            closeQuizModal();
            showGameOverModal();
            return;
        }
        message = `<h3>Incorrect</h3>
                   <p>Score: ${result.score}/${result.total}. You lost a life!</p>
                   <p>You have ${result.lives_left} ${result.lives_left > 1 ? 'lives' : 'life'} left. Try again!</p>`;
    }
    DOM.quizResultEl.innerHTML = message;
}

/**
 * Shows the 'Game Over' modal.
 */
export function showGameOverModal() {
    DOM.gameOverModal.classList.remove('hidden');
    document.body.classList.add('modal-open');
}

/**
 * Opens and populates the training modal with learning resources.
 * @param {object} [data] - Optional training data from the server. If not provided, a loading message is displayed.
 * @param {string} [data.explanation] - A text explanation of the topic.
 * @param {Array<string>} [data.resources] - A list of resource URLs.
 */
export function openTrainingModal(data) {
  DOM.trainingModal.classList.remove('hidden');
  document.body.classList.add('modal-open');

  DOM.trainingTitle.textContent = `Training Room`;
  
  if (!data) {
    DOM.trainingContent.innerHTML = `
      <div class="loading-spinner-container">
        <div class="loading-spinner"></div>
        <p>Loading training materials...</p>
      </div>
    `;
    return;
  }

  let resourcesHtml = '<h3>Recommended Resources</h3><ul>';
  if (data.resources && data.resources.length > 0) {
    data.resources.forEach(url => {
      resourcesHtml += `
        <li>
          <a href="${url}" target="_blank">${url}</a>
        </li>
      `;
    });
  } else {
    resourcesHtml += '<li>No resources found.</li>';
  }
  resourcesHtml += '</ul>';

  DOM.trainingContent.innerHTML = `
    <h3>Core Concepts</h3>
    <p>${data.explanation}</p>
    ${resourcesHtml}
  `;
}

/**
 * Closes the training modal.
 */
export function closeTrainingModal() {
  DOM.trainingModal.classList.add('hidden');
  document.body.classList.remove('modal-open');
}
