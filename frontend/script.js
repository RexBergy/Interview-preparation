// frontend/script.js

/**
 * @file Main entry point for the Interview Quest frontend application.
 * This script orchestrates the entire application flow, wiring up UI elements,
 * handling user interactions, and coordinating with the API and UI modules.
 */

import {
  connectCalendar,
  generatePlan,
  startQuiz,
  submitQuiz,
} from './api.js';
import {
  DOM,
  setMinDates,
  populateTimeSelect,
  populateHoursSelect,
  showStep,
  updatePlanStream,
  updateLoadingStatus,
  loadAndRenderGameBoard,
  openQuizModal,
  closeQuizModal,
  displayQuizResult,
  showQuizLoading,
} from './ui.js';
import { appState } from './state.js';

/**
 * Main application logic, executed once the DOM is fully loaded.
 * It initializes the UI and sets up all necessary event listeners.
 */
document.addEventListener('DOMContentLoaded', () => {
  // --- INITIAL UI SETUP ---
  // Configure form elements with default and valid values.
  appState.useCalendar = false;
  setMinDates();
  populateTimeSelect();
  populateHoursSelect();

  // --- DYNAMIC INTRO ANIMATIONS ---
  const animatedElements = [
    document.querySelector('.app-header'),
    document.querySelector('#setup-step')
  ];

  animatedElements.forEach((el, index) => {
    if (el) {
      el.classList.add('fade-in-slide-up');
      setTimeout(() => {
        el.classList.add('visible');
      }, index * 200); // Stagger the animation
    }
  });


  // --- Multi-page Form Logic ---
  let currentPage = 1;
  const totalPages = DOM.formPages.length;

  const updateFormPage = () => {
    DOM.formPages.forEach(page => {
      const pageNum = parseInt(page.dataset.page, 10);
      page.style.display = pageNum === currentPage ? 'block' : 'none';
    });

    DOM.prevBtn.style.display = currentPage > 1 ? 'block' : 'none';
    DOM.nextBtn.style.display = currentPage < totalPages ? 'block' : 'none';
  };

  DOM.nextBtn.addEventListener('click', () => {
    if (currentPage < totalPages) {
      currentPage++;
      updateFormPage();
    }
  });

  DOM.prevBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      updateFormPage();
    }
  });

  // --- EVENT LISTENERS ---

  const calendarQuestionGroup = DOM.calYesBtn.closest('.form-group');

  /**
   * Handles the "Yes" button click for Google Calendar sync.
   */
  DOM.calYesBtn.addEventListener('click', async () => {
    appState.useCalendar = true;
    try {
      const data = await connectCalendar();
      if (data.auth_url) {
        window.open(data.auth_url, '_blank');
        calendarQuestionGroup.style.display = 'none';
        DOM.generatePlanBtn.style.display = 'block';
      } else {
        // If auth_url is not returned, something is wrong but not an exception
        // We still hide the question and show the button, but don't sync.
        appState.useCalendar = false;
        calendarQuestionGroup.style.display = 'none';
        DOM.generatePlanBtn.style.display = 'block';
      }
    } catch (error) {
      alert(error.message);
      appState.useCalendar = false; // Revert on error
      calendarQuestionGroup.style.display = 'none';
      DOM.generatePlanBtn.style.display = 'block';
    }
  });

  /**
   * Handles the "No" button click for Google Calendar sync.
   */
  DOM.calNoBtn.addEventListener('click', () => {
    appState.useCalendar = false;
    calendarQuestionGroup.style.display = 'none';
    DOM.generatePlanBtn.style.display = 'block';
  });

  /**
   * Handles the main setup form submission.
   * It gathers user input, stores the role in the app state, switches to the loading view,
   * and initiates the plan generation process.
   */
  DOM.setupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(DOM.setupForm);
    const data = Object.fromEntries(formData.entries());
    data.use_cal = appState.useCalendar;
    appState.roleForQuiz = data.role; // Cache role for later use in quizzes.

    showStep('loading');
    updatePlanStream(''); // Clear any previous plan text.

    try {
      const response = await generatePlan(data);
      await processPlanStream(response); // Handle the streaming response.
    } catch (error) {
      alert(error.message);
      showStep('setup'); // On failure, return to the setup screen.
    }
  });

  /**
   * Uses event delegation to handle clicks on "Start" buttons within the quest board.
   * It identifies the clicked quest and initiates the quiz if the quest is active.
   */
  DOM.questBoardBody.addEventListener('click', async (e) => {
    // Ensure the click is on a button with a task index.
    if (e.target.tagName === 'BUTTON' && e.target.dataset.index) {
      const taskIndex = parseInt(e.target.dataset.index, 10);
      const taskStatus = e.target.dataset.status;

      // Prevent starting locked or completed quests.
      if (taskStatus === '🔒 LOCKED' || taskStatus === '✅ DONE') {
        alert(`Quest is ${taskStatus === '✅ DONE' ? 'already completed' : 'locked'}.`);
        return;
      }
      
      try {
        openQuizModal(); // Show loading state
        const quizData = await startQuiz(taskIndex, appState.roleForQuiz);
        openQuizModal(quizData); // Populate with data
      } catch (error) {
        alert(error.message);
        closeQuizModal();
      }
    } else if (e.target.classList.contains('train-btn')) {
      const quest = e.target.dataset.quest;
      const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(quest)}`;
      window.open(searchUrl, '_blank');
    }
  });

  /**
   * Handles the submission of the quiz form.
   * It collects all selected answers and sends them to the server for evaluation.
   */
  DOM.quizForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(DOM.quizForm);
    const answers = Array.from(formData.values());
    
    try {
      const result = await submitQuiz(answers);
      displayQuizResult(result); // Show the outcome to the user.
    } catch (error) {
      alert(error.message);
    }
  });

  /**
   * Handles closing the quiz modal. After closing, it re-fetches and renders
   * the game board to reflect any state changes (e.g., quest completion, life loss).
   */
  DOM.closeQuizBtn.addEventListener('click', async () => {
    closeQuizModal();
    await loadAndRenderGameBoard();
  });

  /**
   * Handles the "Restart" button in the game over modal, simply reloading the page
   * to start a fresh session.
   */
  DOM.restartGameBtn.addEventListener('click', () => {
    window.location.reload();
  });

  // --- HELPER FUNCTIONS ---

  /**
   * Processes the Server-Sent Events (SSE) stream from the plan generation endpoint.
   * It reads chunks of data, parses them, and updates the UI accordingly.
   * @param {Response} response - The raw Response object from the `fetch` call.
   */
  async function processPlanStream(response) {
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    
    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            // Once the stream is finished, load the main game board.
            updateLoadingStatus('Loading game board...');
            await loadAndRenderGameBoard();
            showStep('game-board');
            break;
        }

        // SSE messages are often separated by double newlines.
        const lines = value.split('\n\n').filter(line => line.trim());
        for (const line of lines) {
            const [eventLine, dataLine] = line.split('\n');
            if (!eventLine || !dataLine) continue;

            const eventType = eventLine.replace('event: ', '');
            const eventData = dataLine.replace('data: ', '');

            try {
                const parsedData = JSON.parse(eventData);
                // Update UI based on the event type sent from the server.
                if (eventType === 'plan_chunk') {
                    updatePlanStream(parsedData);
                } else if (eventType === 'status') {
                    updateLoadingStatus(parsedData);
                }
            } catch (e) {
                console.error("Failed to parse SSE data chunk:", eventData);
            }
        }
    }
  }
});