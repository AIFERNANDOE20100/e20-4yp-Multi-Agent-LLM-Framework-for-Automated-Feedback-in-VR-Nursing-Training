const HISTORY_SCRIPTS = {
    focused_history: [
        "Hello, I am here to ask a few questions before wound care.",
        "Can you tell me your name and age?",
        "Do you have any allergies?",
        "What surgery did you have and when was it done?",
        "Are you having any pain at the moment?"
    ],
    short_history: [
        "What procedure did you have?",
        "Do you have any allergies?",
        "How is your pain right now?"
    ]
};

const PROCEDURE_ACTIONS = [
    {
        code: "hand_hygiene_initial",
        label: "Initial Hand Hygiene",
        backendActionType: "action_initial_hand_hygiene"
    },
    {
        code: "clean_trolley",
        label: "Clean Trolley",
        backendActionType: "action_clean_trolley"
    },
    {
        code: "hand_hygiene_again",
        label: "Hand Hygiene Again",
        backendActionType: "action_hand_hygiene_after_cleaning"
    },
    {
        code: "select_solution",
        label: "Select Solution",
        backendActionType: "action_select_solution"
    },
    {
        code: "verify_solution",
        label: "Verify Solution",
        backendActionType: "action_verify_solution"
    },
    {
        code: "select_dressing",
        label: "Select Dressing",
        backendActionType: "action_select_dressing"
    },
    {
        code: "verify_dressing",
        label: "Verify Dressing",
        backendActionType: "action_verify_dressing"
    },
    {
        code: "arrange_materials",
        label: "Arrange Materials",
        backendActionType: "action_arrange_materials"
    },
    {
        code: "bring_trolley",
        label: "Bring Trolley",
        backendActionType: "action_bring_trolley"
    }
];

const state = {
    apiBaseUrl: "http://127.0.0.1:8000",
    wsBaseUrl: "ws://127.0.0.1:8000",
    activeSession: null,
    sessionInfo: null,
    ws: null,
    wsConnected: false,
    logEntries: [],
    lastStructuredResponse: null,
    currentStep: null,
    selectedMcqAnswers: {},
    completedActions: new Set(),
    patientMessages: [],
    nurseMessages: [],
    historyTransitionPendingConfirmation: false,
    autoPollHandle: null,
    scriptRunning: false
};

function qs(id) {
    return document.getElementById(id);
}

function sanitizeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function getApiBaseUrl() {
    return qs("apiBaseUrl").value.trim().replace(/\/$/, "");
}

function getWsBaseUrl() {
    return qs("wsBaseUrl").value.trim().replace(/\/$/, "");
}

async function apiCall(path) {
    const response = await fetch(`${state.apiBaseUrl}${path}`);
    if (!response.ok) {
        let detail = response.statusText;
        try {
            const data = await response.json();
            detail = data.detail || JSON.stringify(data);
        } catch (error) {
            detail = response.statusText;
        }
        throw new Error(detail);
    }
    return response.json();
}

function setStructuredResponse(payload) {
    state.lastStructuredResponse = payload;
    qs("structuredResponse").textContent = JSON.stringify(payload, null, 2);
    qs("structuredResponse").classList.remove("empty-state");
}

function appendLog(direction, payload, label) {
    const timestamp = new Date().toLocaleTimeString();
    state.logEntries.push({
        timestamp,
        direction,
        label,
        payload
    });

    const consoleEl = qs("logConsole");
    if (consoleEl.querySelector(".empty-state")) {
        consoleEl.innerHTML = "";
    }

    const entry = document.createElement("div");
    entry.className = `log-entry ${direction}`;
    entry.innerHTML = `
        <div class="log-meta">${sanitizeHtml(timestamp)} | ${sanitizeHtml(direction.toUpperCase())} | ${sanitizeHtml(label)}</div>
        <div>${sanitizeHtml(JSON.stringify(payload, null, 2))}</div>
    `;
    consoleEl.prepend(entry);
}

function updateConnectionUi() {
    qs("wsStatus").textContent = state.wsConnected ? "Connected" : "Disconnected";
    qs("wsStatus").className = `status-value ${state.wsConnected ? "connected" : "disconnected"}`;
    qs("connectSessionBtn").disabled = state.wsConnected || !state.activeSession?.session_id;
    qs("disconnectSessionBtn").disabled = !state.wsConnected;
}

function updateSessionStrip() {
    const active = state.activeSession;
    const info = state.sessionInfo;

    qs("sessionId").textContent = active?.session_id || info?.session_id || "-";
    qs("sessionToken").textContent = active?.session_token || info?.session_token || "-";
    qs("scenarioId").textContent = active?.scenario_id || info?.scenario_id || "-";
    qs("currentStep").textContent = state.currentStep || info?.current_step || "-";
}

function renderActiveSessionStatus(message) {
    qs("activeSessionStatus").textContent = message;
}

function setPanelState(step) {
    const steps = ["history", "assessment", "cleaning_and_dressing"];
    const mapping = {
        history: "historyStepState",
        assessment: "assessmentStepState",
        cleaning_and_dressing: "cleaningStepState"
    };

    steps.forEach(item => {
        const el = qs(mapping[item]);
        const isActive = step === item;
        el.textContent = isActive ? "Active" : "Inactive";
        el.className = `panel-step${isActive ? " active" : ""}`;
    });

    qs("historyPanel").style.opacity = step && step !== "history" ? "0.78" : "1";
    qs("assessmentPanel").style.opacity = step && step !== "assessment" ? "0.78" : "1";
    qs("cleaningPanel").style.opacity = step && step !== "cleaning_and_dressing" ? "0.78" : "1";
}

function renderMessageStream(containerId, items, roleLabel) {
    const container = qs(containerId);
    if (!items.length) {
        container.innerHTML = `<div class="empty-state">No ${sanitizeHtml(roleLabel)} yet.</div>`;
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="message-item">
            <div class="message-role">${sanitizeHtml(item.role)}</div>
            <div>${sanitizeHtml(item.text)}</div>
        </div>
    `).join("");
}

function renderStructuredBox(containerId, payload) {
    const container = qs(containerId);
    if (!payload) {
        container.innerHTML = '<div class="empty-state">No data yet.</div>';
        return;
    }

    const rows = Object.entries(payload).map(([key, value]) => `
        <div class="feedback-item">
            <div class="feedback-key">${sanitizeHtml(key)}</div>
            <div>${sanitizeHtml(typeof value === "object" ? JSON.stringify(value, null, 2) : String(value))}</div>
        </div>
    `).join("");

    container.innerHTML = rows;
}

function renderMcqs() {
    const container = qs("mcqContainer");
    const questions = state.sessionInfo?.scenario_metadata?.assessment_questions || [];

    if (!questions.length) {
        container.innerHTML = '<div class="empty-state">No assessment questions available.</div>';
        return;
    }

    container.innerHTML = questions.map((question, index) => {
        const selected = state.selectedMcqAnswers[question.id]?.answer;
        const result = state.selectedMcqAnswers[question.id]?.result;
        const cardClass = result?.status || "";

        return `
            <div class="mcq-card ${sanitizeHtml(cardClass)}" id="mcq-${sanitizeHtml(question.id)}">
                <p class="mcq-question">${index + 1}. ${sanitizeHtml(question.question)}</p>
                <div class="mcq-options">
                    ${question.options.map(option => `
                        <button
                            class="mcq-option ${selected === option ? "selected" : ""}"
                            data-question-id="${sanitizeHtml(question.id)}"
                            data-answer="${sanitizeHtml(option)}"
                        >
                            ${sanitizeHtml(option)}
                        </button>
                    `).join("")}
                </div>
                <div class="mcq-feedback">
                    ${result ? `
                        <strong>${result.is_correct ? "Correct" : "Incorrect"}.</strong>
                        ${sanitizeHtml(result.explanation || "")}
                    ` : "Awaiting answer."}
                </div>
            </div>
        `;
    }).join("");

    container.querySelectorAll(".mcq-option").forEach(button => {
        button.addEventListener("click", () => {
            submitMcqAnswer(button.dataset.questionId, button.dataset.answer);
        });
    });
}

function renderActionButtons() {
    const container = qs("actionGrid");
    container.innerHTML = PROCEDURE_ACTIONS.map(action => {
        const completed = state.completedActions.has(action.backendActionType);
        return `
            <button
                class="action-button active-step ${completed ? "completed" : ""}"
                data-action-code="${sanitizeHtml(action.code)}"
                data-action-type="${sanitizeHtml(action.backendActionType)}"
            >
                <strong>${sanitizeHtml(action.label)}</strong>
                <span class="action-code">${sanitizeHtml(action.code)}</span>
            </button>
        `;
    }).join("");

    container.querySelectorAll(".action-button").forEach(button => {
        button.addEventListener("click", () => {
            submitAction(button.dataset.actionCode, button.dataset.actionType);
        });
    });
}

async function refreshActiveSession() {
    state.apiBaseUrl = getApiBaseUrl();
    state.wsBaseUrl = getWsBaseUrl();

    try {
        const active = await apiCall("/session/active");
        state.activeSession = active?.session_id ? active : null;
        if (state.activeSession) {
            renderActiveSessionStatus(
                `Active session found: ${state.activeSession.session_id} for scenario ${state.activeSession.scenario_id}.`
            );
        } else {
            renderActiveSessionStatus("No active session. Waiting for Teacher Portal to start one.");
        }
        updateSessionStrip();
        updateConnectionUi();
    } catch (error) {
        renderActiveSessionStatus(`Failed to check active session: ${error.message}`);
        appendLog("error", { message: error.message }, "active_session_error");
    }
}

async function refreshSessionDetails() {
    const sessionId = state.activeSession?.session_id || state.sessionInfo?.session_id;
    if (!sessionId) {
        return;
    }

    try {
        const info = await apiCall(`/session/${sessionId}`);
        state.sessionInfo = info;
        state.currentStep = info.current_step;
        updateSessionStrip();
        setPanelState(state.currentStep);
        renderMcqs();
        renderActionButtons();
    } catch (error) {
        appendLog("error", { message: error.message }, "session_info_error");
    }
}

function connectToActiveSession() {
    const active = state.activeSession;
    if (!active?.session_id || !active?.session_token) {
        renderActiveSessionStatus("No connectable active session found.");
        return;
    }

    if (state.ws && [WebSocket.OPEN, WebSocket.CONNECTING].includes(state.ws.readyState)) {
        return;
    }

    const wsUrl = `${state.wsBaseUrl}/ws/session/${encodeURIComponent(active.session_id)}?token=${encodeURIComponent(active.session_token)}`;
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = async () => {
        state.wsConnected = true;
        updateConnectionUi();
        appendLog("received", { message: "socket_open" }, "socket_open");
        await refreshSessionDetails();
    };

    state.ws.onmessage = async event => {
        try {
            const payload = JSON.parse(event.data);
            appendLog("received", payload, payload.event || payload.type || "message");
            setStructuredResponse(payload);
            await handleServerMessage(payload);
        } catch (error) {
            appendLog("error", { message: error.message }, "parse_error");
        }
    };

    state.ws.onerror = () => {
        appendLog("error", { message: "WebSocket error" }, "socket_error");
    };

    state.ws.onclose = () => {
        state.wsConnected = false;
        updateConnectionUi();
        appendLog("received", { message: "socket_closed" }, "socket_closed");
    };
}

function disconnectSession() {
    if (state.ws) {
        state.ws.close();
    }
    state.ws = null;
    state.wsConnected = false;
    updateConnectionUi();
}

function sendEvent(eventName, data = {}) {
    if (!state.wsConnected || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
        appendLog("error", { message: "WebSocket is not connected" }, eventName);
        return false;
    }

    const payload = {
        type: "event",
        event: eventName,
        data
    };

    state.ws.send(JSON.stringify(payload));
    appendLog("sent", payload, eventName);
    return true;
}

async function submitHistoryMessage() {
    if (state.currentStep !== "history") {
        return;
    }

    const input = qs("historyMessageInput");
    const text = input.value.trim();
    if (!text) {
        return;
    }

    const sent = sendEvent("text_message", { text });
    if (sent) {
        input.value = "";
    }
}

function submitMcqAnswer(questionId, answer) {
    if (state.currentStep !== "assessment") {
        return;
    }

    state.selectedMcqAnswers[questionId] = {
        ...(state.selectedMcqAnswers[questionId] || {}),
        answer
    };
    renderMcqs();
    sendEvent("mcq_answer", { question_id: questionId, answer });
}

function submitAction(actionCode, backendActionType) {
    if (state.currentStep !== "cleaning_and_dressing") {
        return;
    }

    sendEvent("action_performed", {
        action_type: backendActionType,
        action: actionCode
    });
}

function completeCurrentStep() {
    if (!state.currentStep) {
        return;
    }
    sendEvent("step_complete", { step: state.currentStep });
}

function confirmHistoryTransition() {
    if (!state.historyTransitionPendingConfirmation) {
        return;
    }
    sendEvent("confirm_step_transition");
}

async function handleServerMessage(message) {
    if (message.type === "error") {
        return;
    }

    const data = message.data || {};

    switch (message.event) {
        case "nurse_message":
            if (data.role === "patient") {
                state.patientMessages.unshift({ role: "patient", text: data.text || "" });
                renderMessageStream("historyResponses", state.patientMessages, "patient responses");
            } else if (data.text) {
                state.nurseMessages.unshift({ role: data.role || "nurse", text: data.text });
                renderMessageStream("nurseResponses", state.nurseMessages, "nurse response");
            }
            break;

        case "mcq_answer_result":
            state.selectedMcqAnswers[data.question_id] = {
                ...(state.selectedMcqAnswers[data.question_id] || {}),
                result: data
            };
            renderMcqs();
            break;

        case "real_time_feedback":
            if (data.action_recorded && data.action_type) {
                state.completedActions.add(data.action_type);
                renderActionButtons();
            }
            renderStructuredBox("cleaningFeedback", data);
            break;

        case "final_feedback":
            state.historyTransitionPendingConfirmation = true;
            qs("confirmHistoryTransitionBtn").disabled = false;
            renderStructuredBox("historyFeedback", data);
            break;

        case "assessment_summary":
            renderStructuredBox("assessmentSummary", data);
            break;

        case "step_complete":
            state.historyTransitionPendingConfirmation = false;
            qs("confirmHistoryTransitionBtn").disabled = true;
            if (data.next_step) {
                state.currentStep = data.next_step;
                if (data.next_step === "completed") {
                    renderStructuredBox("assessmentSummary", {
                        status: "completed",
                        session_id: state.sessionInfo?.session_id || state.activeSession?.session_id
                    });
                }
            }
            await refreshSessionDetails();
            break;

        case "session_end":
            state.currentStep = "completed";
            if (state.sessionInfo) {
                state.sessionInfo.current_step = "completed";
            }
            updateSessionStrip();
            setPanelState("completed");
            break;

        default:
            break;
    }
}

async function loadHistoryScript() {
    const selected = qs("historyScriptSelect").value;
    const lines = HISTORY_SCRIPTS[selected] || [];
    qs("historyScriptEditor").value = lines.join("\n");
}

async function runHistoryScript() {
    if (state.currentStep !== "history" || state.scriptRunning) {
        return;
    }

    const lines = qs("historyScriptEditor").value
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean);

    if (!lines.length) {
        return;
    }

    state.scriptRunning = true;
    try {
        for (const line of lines) {
            qs("historyMessageInput").value = line;
            await submitHistoryMessage();
            await sleep(700);
        }
    } finally {
        state.scriptRunning = false;
    }
}

async function runMcqScript(mode) {
    if (state.currentStep !== "assessment") {
        return;
    }

    const questions = state.sessionInfo?.scenario_metadata?.assessment_questions || [];
    for (const question of questions) {
        const answer = mode === "correct"
            ? question.correct_answer
            : question.options?.[0];
        if (answer) {
            submitMcqAnswer(question.id, answer);
            await sleep(250);
        }
    }
}

async function runActionSequence() {
    if (state.currentStep !== "cleaning_and_dressing") {
        return;
    }

    for (const action of PROCEDURE_ACTIONS) {
        submitAction(action.code, action.backendActionType);
        await sleep(350);
    }
}

async function exportSessionLog() {
    const sessionId = state.activeSession?.session_id || state.sessionInfo?.session_id;
    let backendLog = null;

    if (sessionId) {
        try {
            backendLog = await apiCall(`/session/${sessionId}/log`);
        } catch (error) {
            backendLog = { error: error.message };
        }
    }

    const exportPayload = {
        exported_at: new Date().toISOString(),
        api_base_url: state.apiBaseUrl,
        ws_base_url: state.wsBaseUrl,
        active_session: state.activeSession,
        session_info: state.sessionInfo,
        current_step: state.currentStep,
        selected_mcq_answers: state.selectedMcqAnswers,
        completed_actions: Array.from(state.completedActions),
        websocket_log: state.logEntries,
        last_structured_response: state.lastStructuredResponse,
        backend_session_log: backendLog
    };

    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${sessionId || "session"}-evaluation-log.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function clearLog() {
    state.logEntries = [];
    qs("logConsole").innerHTML = '<div class="empty-state">No WebSocket traffic yet.</div>';
}

function populateHistoryScripts() {
    const select = qs("historyScriptSelect");
    select.innerHTML = Object.keys(HISTORY_SCRIPTS).map(key => `
        <option value="${sanitizeHtml(key)}">${sanitizeHtml(key)}</option>
    `).join("");
    loadHistoryScript();
}

function startAutoPoll() {
    if (state.autoPollHandle) {
        clearInterval(state.autoPollHandle);
    }
    state.autoPollHandle = setInterval(() => {
        if (!state.wsConnected) {
            refreshActiveSession();
        }
    }, 5000);
}

function bindEvents() {
    qs("refreshActiveSessionBtn").addEventListener("click", refreshActiveSession);
    qs("connectSessionBtn").addEventListener("click", connectToActiveSession);
    qs("disconnectSessionBtn").addEventListener("click", disconnectSession);
    qs("refreshSessionDetailsBtn").addEventListener("click", refreshSessionDetails);
    qs("sendHistoryMessageBtn").addEventListener("click", submitHistoryMessage);
    qs("historyMessageInput").addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            submitHistoryMessage();
        }
    });
    qs("completeHistoryBtn").addEventListener("click", completeCurrentStep);
    qs("confirmHistoryTransitionBtn").addEventListener("click", confirmHistoryTransition);
    qs("completeAssessmentBtn").addEventListener("click", completeCurrentStep);
    qs("completeCleaningBtn").addEventListener("click", completeCurrentStep);
    qs("answerAllCorrectBtn").addEventListener("click", () => runMcqScript("correct"));
    qs("answerAllFirstBtn").addEventListener("click", () => runMcqScript("first"));
    qs("runActionSequenceBtn").addEventListener("click", runActionSequence);
    qs("loadHistoryScriptBtn").addEventListener("click", loadHistoryScript);
    qs("runHistoryScriptBtn").addEventListener("click", runHistoryScript);
    qs("exportJsonBtn").addEventListener("click", exportSessionLog);
    qs("clearLogBtn").addEventListener("click", clearLog);
    qs("apiBaseUrl").addEventListener("change", refreshActiveSession);
    qs("wsBaseUrl").addEventListener("change", refreshActiveSession);
}

function initializeUi() {
    populateHistoryScripts();
    renderMcqs();
    renderActionButtons();
    updateSessionStrip();
    updateConnectionUi();
    setPanelState(null);
    bindEvents();
    startAutoPoll();
    refreshActiveSession();
}

window.addEventListener("beforeunload", () => {
    if (state.autoPollHandle) {
        clearInterval(state.autoPollHandle);
    }
    disconnectSession();
});

document.addEventListener("DOMContentLoaded", initializeUi);
