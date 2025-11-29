document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENTS ---
    const setupStep = document.getElementById('setup-step');
    const loadingStep = document.getElementById('loading-step');
    const gameBoardStep = document.getElementById('game-board-step');
    const setupForm = document.getElementById('setup-form');
    const useCalCheckbox = document.getElementById('use_cal');
    const connectCalBtn = document.getElementById('connect-cal-btn');
    const planStreamEl = document.getElementById('plan-stream');
    const loadingStatusEl = document.getElementById('loading-status');
    const questBoardBody = document.querySelector('#quest-board-table tbody');
    const playerStatsEl = document.getElementById('player-stats');
    const quizModal = document.getElementById('quiz-modal');
    const quizForm = document.getElementById('quiz-form');
    const quizTitle = document.getElementById('quiz-title');
    const quizQuestionsContainer = document.getElementById('quiz-questions-container');
    const quizResultEl = document.getElementById('quiz-result');
    const closeQuizBtn = document.getElementById('close-quiz-btn');
    const gameOverModal = document.getElementById('game-over-modal');

    let roleForQuiz = '';

    // --- INITIAL SETUP ---
    function setMinDates() {
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('start_date').setAttribute('min', today);
        document.getElementById('start_date').value = today;
        document.getElementById('interview_date').setAttribute('min', today);
    }

    function populateTimeSelect() {
        const select = document.getElementById('pref_time');
        for (let i = 7; i <= 21; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = `${i}:00 (${i < 12 ? i + ' AM' : (i === 12 ? '12 PM' : i - 12 + ' PM')})`;
            if (i === 9) option.selected = true;
            select.appendChild(option);
        }
    }

    setMinDates();
    populateTimeSelect();

    // --- EVENT LISTENERS ---
    useCalCheckbox.addEventListener('change', () => {
        connectCalBtn.disabled = !useCalCheckbox.checked;
    });

    connectCalBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/connect_calendar');
            const data = await response.json();
            if (data.auth_url) {
                window.open(data.auth_url, '_blank');
                connectCalBtn.textContent = 'Connected!';
                connectCalBtn.disabled = true;
            }
        } catch (error) {
            console.error('Error connecting to calendar:', error);
            alert('Could not connect to Google Calendar.');
        }
    });

    setupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(setupForm);
        const data = Object.fromEntries(formData.entries());
        data.use_cal = useCalCheckbox.checked;
        roleForQuiz = data.role;

        setupStep.classList.add('hidden');
        loadingStep.classList.remove('hidden');

        planStreamEl.textContent = '';

        // Use fetch for POST request with streaming response
        const response = await fetch('/generate_plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.body) {
            loadingStatusEl.textContent = 'Error: Response body is not available.';
            return;
        }

        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                loadingStatusEl.textContent = 'Loading game board...';
                await loadGameBoard();
                loadingStep.classList.add('hidden');
                gameBoardStep.classList.remove('hidden');
                break;
            }

            // Process SSE chunks
            const lines = value.split('\n\n').filter(line => line.trim());
            for (const line of lines) {
                const [eventLine, dataLine] = line.split('\n');
                if (!eventLine || !dataLine) continue;

                const eventType = eventLine.replace('event: ', '');
                const eventData = dataLine.replace('data: ', '');

                try {
                    const parsedData = JSON.parse(eventData);
                    if (eventType === 'plan_chunk') {
                        planStreamEl.textContent += parsedData;
                        planStreamEl.scrollTop = planStreamEl.scrollHeight;
                    } else if (eventType === 'status') {
                        loadingStatusEl.textContent = parsedData;
                    } else if (eventType === 'complete') {
                        // The 'done' condition of the reader will handle this.
                    }
                } catch (e) {
                    console.error("Failed to parse SSE data:", eventData);
                }
            }
        }
    });

    questBoardBody.addEventListener('click', async (e) => {
        if (e.target.tagName === 'BUTTON' && e.target.dataset.index) {
            const taskIndex = parseInt(e.target.dataset.index, 10);
            const taskStatus = e.target.dataset.status;

            if (taskStatus === '🔒 LOCKED' || taskStatus === '✅ DONE') {
                alert(`Quest is ${taskStatus === '✅ DONE' ? 'already completed' : 'locked'}.`);
                return;
            }
            
            openQuizModal(taskIndex);
        }
    });

    quizForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(quizForm);
        const answers = Array.from(formData.values());
        
        const response = await fetch('/quiz/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });
        const result = await response.json();
        
        displayQuizResult(result);
    });

    closeQuizBtn.addEventListener('click', async () => {
        quizModal.classList.add('hidden');
        await loadGameBoard();
    });

    document.getElementById('restart-game-btn').addEventListener('click', () => {
        window.location.reload();
    });

    // --- RENDER FUNCTIONS ---
    async function loadGameBoard() {
        try {
            const response = await fetch('/game_state');
            if (!response.ok) throw new Error('Failed to load game state');
            const state = await response.json();
            renderPlayerStats(state.stats);
            renderQuestBoard(state.board);
        } catch (error) {
            console.error(error);
            alert('Could not load game board. Please try generating a new plan.');
        }
    }

    function renderPlayerStats(stats) {
        const progressPercent = stats.xp_per_level > 0 ? (stats.xp_in_level / stats.xp_per_level) * 100 : 0;
        playerStatsEl.innerHTML = `
            <h3>Level ${stats.level} ${stats.title}</h3>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${progressPercent}%">${stats.xp_in_level} / ${stats.xp_per_level} XP</div>
            </div>
            <p>Lives: ${'❤️'.repeat(stats.lives)} | Total XP: ✨ ${stats.xp}</p>
        `;
    }

    function renderQuestBoard(board) {
        questBoardBody.innerHTML = '';
        board.forEach((task, index) => {
            const row = document.createElement('tr');
            const isClickable = task.Status !== '🔒 LOCKED' && task.Status !== '✅ DONE';
            row.innerHTML = `
                <td>${task.Status}</td>
                <td>${task.Timeline}</td>
                <td>${task['Quest Objective']}</td>
                <td>${task.Rewards}</td>
                <td>
                    <button data-index="${index}" data-status="${task.Status}" ${!isClickable ? 'disabled' : ''}>
                        ${task.Status === '✅ DONE' ? 'Completed' : 'Start'}
                    </button>
                </td>
            `;
            questBoardBody.appendChild(row);
        });
    }

    async function openQuizModal(taskIndex) {
        try {
            const response = await fetch('/start_quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_index: taskIndex, role: roleForQuiz })
            });
            if (!response.ok) throw new Error('Failed to load quiz');
            const data = await response.json();

            quizTitle.textContent = `⚔️ Quest: ${data.task_name}`;
            quizQuestionsContainer.innerHTML = '';
            data.questions.forEach((q, i) => {
                const questionDiv = document.createElement('div');
                questionDiv.className = 'quiz-question';
                let optionsHtml = q.options.map((opt, j) => `
                    <label>
                        <input type="radio" name="q${i}" value="${opt}" required>
                        ${opt}
                    </label>
                `).join('');
                questionDiv.innerHTML = `
                    <p>${i + 1}. ${q.q}</p>
                    <div class="quiz-options">${optionsHtml}</div>
                `;
                quizQuestionsContainer.appendChild(questionDiv);
            });

            quizResultEl.classList.add('hidden');
            closeQuizBtn.classList.add('hidden');
            quizForm.classList.remove('hidden');
            quizModal.classList.remove('hidden');

        } catch (error) {
            console.error(error);
            alert('Could not start the quiz for this quest.');
        }
    }

    function displayQuizResult(result) {
        quizForm.classList.add('hidden');
        quizResultEl.classList.remove('hidden');
        closeQuizBtn.classList.remove('hidden');

        let message = '';
        if (result.passed) {
            quizResultEl.className = 'result-success';
            message = `<h3>🎉 Victory! Quest Complete! 🎉</h3>
                       <p>Score: ${result.score}/${result.total}</p>`;
        } else {
            quizResultEl.className = 'result-fail';
            if (result.game_over) {
                quizModal.classList.add('hidden');
                gameOverModal.classList.remove('hidden');
                return;
            }
            message = `<h3>Incorrect</h3>
                       <p>Score: ${result.score}/${result.total}. You lost a life!</p>
                       <p>You have ${result.lives_left} ${result.lives_left > 1 ? 'lives' : 'life'} left. Try again!</p>`;
            // Allow retrying by just closing the modal
        }
        quizResultEl.innerHTML = message;
    }
});