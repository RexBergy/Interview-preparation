// frontend/api.js

/**
 * @file Manages all API interactions for the Interview Quest application.
 * This module abstracts the logic for making network requests to the backend server,
 * handling data fetching, and error management in a centralized location.
 * @author Gemini
 */

/**
 * The base URL for all API requests.
 * It defaults to the current window's origin, making it adaptable to different deployment environments.
 * @type {string}
 */
const API_BASE_URL = window.location.origin;

/**
 * Initiates the Google Calendar connection process by fetching an auth URL from the backend.
 * @returns {Promise<object>} A promise that resolves with the authentication URL data, e.g., { auth_url: "..." }.
 * @throws {Error} If the network request fails or the server returns an error status.
 */
export async function connectCalendar() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/connect_calendar`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error connecting to calendar:', error);
    throw new Error('Could not connect to Google Calendar. Please check the console for more details.');
  }
}

/**
 * Sends user-defined setup data to the backend to generate a personalized study plan.
 * @param {object} setupData - The user's setup data, including role, goal, job description, etc.
 * @returns {Promise<Response>} A promise that resolves with the raw, streaming Response object from the server.
 * @throws {Error} If the request fails or the server returns a non-ok status.
 */
export async function generatePlan(setupData) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/generate_plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(setupData),
    });
    if (!response.ok || !response.body) {
      throw new Error('Failed to get a valid streaming response from the server.');
    }
    return response;
  } catch (error) {
    console.error('Error generating plan:', error);
    throw new Error('Could not generate the quest plan. Please ensure the backend is running.');
  }
}

/**
 * Fetches the complete, current game state from the server.
 * This includes player stats (level, XP, lives) and the quest board.
 * @returns {Promise<object>} A promise that resolves with the full game state data.
 * @throws {Error} If the request fails or the server returns an error.
 */
export async function getGameState() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/game_state`);
    if (!response.ok) {
      throw new Error('Failed to load game state from the server.');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching game state:', error);
    throw new Error('Could not load game board. Please try generating a new plan.');
  }
}

/**
 * Requests a new quiz from the server for a specific task.
 * @param {number} taskIndex - The index of the task/quest to start the quiz for.
 * @param {string} role - The user's target role, used to tailor quiz questions.
 * @returns {Promise<object>} A promise that resolves with the quiz data, including the task name and a list of questions.
 * @throws {Error} If the request fails or the server cannot generate a quiz.
 */
export async function startQuiz(taskIndex, role) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/start_quiz`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_index: taskIndex, role }),
    });
    const quizData = await response.json();
    console.log("startQuiz received:", quizData);
    return quizData;
  } catch (error) {
    console.error('Error starting quiz:', error);
    throw new Error('Could not start the quiz for this quest. The server might be busy.');
  }
}

/**
 * Submits the user's quiz answers to the server for evaluation.
 * @param {string[]} answers - An array of the user's selected answers.
 * @returns {Promise<object>} A promise that resolves with the quiz result, including pass/fail status, score, and game state changes.
 * @throws {Error} If the submission fails or the server returns an error.
 */
export async function submitQuiz(answers) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/quiz/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error submitting quiz:', error);
    throw new Error('Could not submit your answers. Please check your network connection.');
  }
}

export async function trainOnQuest(quest) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quest: quest }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const trainingData = await response.json();
    console.log("trainOnQuest received:", trainingData);
    return trainingData;
  } catch (error) {
    console.error('Error getting training materials:', error);
    throw new Error('Could not get training materials. Please check your network connection.');
  }
}
