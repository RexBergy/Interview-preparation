// frontend/state.js

/**
 * @file Manages the client-side state for the Interview Quest application.
 * This module provides a simple, centralized object to hold application-wide data
 * that needs to be accessed by different modules.
 */

/**
 * A simple, mutable state object to hold application-wide data.
 * This serves as a lightweight, shared memory space for the frontend.
 * @property {string} roleForQuiz - The target role selected by the user (e.g., "Software Engineer").
 * This is cached here when the plan is generated and sent with quiz requests
 * to ensure questions are relevant to the user's goals.
 */
export const appState = {
  roleForQuiz: '',
  preloadedQuizzes: {},    // Stores quizzes, keyed by taskIndex
  preloadedTraining: {},   // Stores training material, keyed by quest string
  currentQuestBoard: [],   // To store the latest quest board for determining next quests
};
