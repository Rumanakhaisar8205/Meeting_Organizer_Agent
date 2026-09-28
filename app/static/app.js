/**
 * Meeting Organizer Agent - Client Application Logic
 * Communicates with FastAPI REST Backend (/api/sessions/...)
 */

let currentSessionId = null;
let currentSessionState = null;
let activeFormatTab = 'markdown';

// Preset prompt applier
function applyPreset(type) {
    const input = document.getElementById('request-input');
    if (type === 'committee') {
        input.value = "Schedule a committee review with Faculty Advisor and HoD to discuss exam guidelines on 2026-09-07 for 45 minutes";
    } else if (type === 'sprint') {
        input.value = "Schedule a 60m sprint planning meeting with Alice, Bob, and Charlie on 2026-09-08";
    } else if (type === 'standup') {
        input.value = "Schedule a 15m daily standup meeting with Alice, Bob, and Charlie on Monday";
    } else if (type === 'vague') {
        input.value = "Schedule a meeting to discuss project planning";
    }
}

// 1. Start Session Request
async function handleStartSession(event) {
    event.preventDefault();
    const requestText = document.getElementById('request-input').value.trim();
    if (!requestText) return;

    try {
        const res = await fetch('/api/sessions/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request: requestText })
        });
        const data = await res.json();
        currentSessionId = data.session_id;
        updateUIState(data);
    } catch (err) {
        alert('Error starting session: ' + err.message);
    }
}

// 2. Clarification Submission
async function handleClarifySession(event) {
    event.preventDefault();
    if (!currentSessionId) return;

    const answers = {};
    const inputs = document.querySelectorAll('#clarification-fields input, #clarification-fields select');
    inputs.forEach(input => {
        if (input.value.trim()) {
            answers[input.name] = input.name === 'duration_minutes' ? parseInt(input.value) : input.value.trim();
        }
    });

    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/clarify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });
        const data = await res.json();
        updateUIState(data);
    } catch (err) {
        alert('Error submitting clarification: ' + err.message);
    }
}

// 3. Plan Revision (Lab 1)
async function handleReviseSession(event) {
    event.preventDefault();
    if (!currentSessionId) return;

    const feedbackInput = document.getElementById('revision-input');
    const feedback = feedbackInput.value.trim();
    if (!feedback) return;

    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/revise`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback })
        });
        const data = await res.json();
        feedbackInput.value = '';
        updateUIState(data);
    } catch (err) {
        alert('Error revising plan: ' + err.message);
    }
}

// 4. Human Approval Gate (Lab 2)
async function handleApproveSession() {
    if (!currentSessionId) return;

    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ approved: true, notes: "Explicitly approved via Web UI" })
        });
        const data = await res.json();
        updateUIState(data);
    } catch (err) {
        alert('Error approving plan: ' + err.message);
    }
}

// 5. Time Slot Selection
async function handleSelectSlot(choiceIndex) {
    if (!currentSessionId) return;

    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/select-slot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ choice: choiceIndex })
        });
        const data = await res.json();
        updateUIState(data);
    } catch (err) {
        alert('Error selecting slot: ' + err.message);
    }
}

// UI State Updater
async function updateUIState(sessionData) {
    currentSessionState = sessionData;

    // Toggle Clarification Drawer
    const drawer = document.getElementById('clarification-drawer');
    const fieldsContainer = document.getElementById('clarification-fields');
    if (sessionData.missing_fields && sessionData.missing_fields.length > 0) {
        drawer.classList.remove('hidden');
        fieldsContainer.innerHTML = '';
        sessionData.missing_fields.forEach((field, idx) => {
            const question = sessionData.clarification_questions[idx] || `Please enter ${field}:`;
            const div = document.createElement('div');
            div.className = 'form-group';
            div.innerHTML = `
                <label>${question}</label>
                <input type="${field === 'duration_minutes' ? 'number' : 'text'}" name="${field}" placeholder="${field}" required>
            `;
            fieldsContainer.appendChild(div);
        });
    } else {
        drawer.classList.add('hidden');
    }

    // Render Plan Card
    const emptyState = document.getElementById('plan-empty-state');
    const planCard = document.getElementById('plan-card');

    if (sessionData.plan) {
        emptyState.classList.add('hidden');
        planCard.classList.remove('hidden');

        document.getElementById('plan-id-badge').innerText = `ID: ${sessionData.plan.meeting_id}`;
        document.getElementById('plan-title').innerText = sessionData.plan.title;
        document.getElementById('plan-date').innerText = sessionData.plan.date;
        document.getElementById('plan-duration').innerText = `${sessionData.plan.duration_minutes} mins`;
        document.getElementById('plan-participants').innerText = sessionData.plan.participants.join(', ');
        
        const slotEl = document.getElementById('plan-timeslot');
        slotEl.innerText = sessionData.plan.time_slot;
        slotEl.className = sessionData.plan.status === 'confirmed' ? 'confirmed-slot' : 'pending-slot';

        const statusPill = document.getElementById('plan-status-pill');
        statusPill.innerText = sessionData.plan.status;
        statusPill.className = `status-pill ${sessionData.plan.status}`;

        // Render Agenda
        const agendaContainer = document.getElementById('plan-agenda-list');
        agendaContainer.innerHTML = '';
        sessionData.plan.agenda.forEach((item, i) => {
            const div = document.createElement('div');
            div.className = 'timeline-item';
            div.innerHTML = `
                <div class="timeline-header">
                    <span>${i + 1}. ${item.title}</span>
                    <span>${item.duration_minutes}m</span>
                </div>
                <div class="timeline-desc">${item.objective}</div>
            `;
            agendaContainer.appendChild(div);
        });

        // Render Action Items (Lab 4)
        const actionItemsContainer = document.getElementById('plan-action-items-list');
        actionItemsContainer.innerHTML = '';
        if (sessionData.plan.minutes_outline && sessionData.plan.minutes_outline.action_items) {
            sessionData.plan.minutes_outline.action_items.forEach(ai => {
                const desc = typeof ai === 'string' ? ai : (ai.description || 'Action Item');
                const owner = typeof ai === 'object' && ai.owner ? ai.owner : 'Assigned';
                const deadline = typeof ai === 'object' && ai.deadline ? ai.deadline : 'Pending';
                
                const div = document.createElement('div');
                div.className = 'action-card';
                div.innerHTML = `
                    <div><strong>${desc}</strong></div>
                    <div class="action-meta">Owner: ${owner} | Due: ${deadline}</div>
                `;
                actionItemsContainer.appendChild(div);
            });
        }

        // Render Memory Widget (Lab 4)
        const memoryWidget = document.getElementById('memory-widget');
        const memoryContent = document.getElementById('memory-insights-content');
        if (memoryWidget && memoryContent) {
            memoryWidget.classList.remove('hidden');
            const actionCount = sessionData.plan.minutes_outline && sessionData.plan.minutes_outline.action_items ? sessionData.plan.minutes_outline.action_items.length : 0;
            memoryContent.innerHTML = `
                <div style="font-size:12px; color:var(--text-secondary); line-height:1.6;">
                    <p><i class="fa-solid fa-database" style="color:var(--accent-blue)"></i> <strong>Knowledge Store:</strong> Matched reference policies & guidelines for "${sessionData.plan.title}".</p>
                    <p style="margin-top:6px;"><i class="fa-solid fa-clock-rotate-left" style="color:var(--accent-purple)"></i> <strong>Meeting History:</strong> Retrieved prior related meetings and carried over <strong>${actionCount}</strong> open action item(s).</p>
                </div>
            `;
        }
    } else {
        emptyState.classList.remove('hidden');
        planCard.classList.add('hidden');
        const memoryWidget = document.getElementById('memory-widget');
        if (memoryWidget) memoryWidget.classList.add('hidden');
    }

    // Toggle Approval Gate & Candidate Slots (Lab 2)
    const gateBanner = document.getElementById('approval-gate-banner');
    const slotCard = document.getElementById('slot-selection-card');
    const confirmedCard = document.getElementById('confirmed-card');

    gateBanner.classList.add('hidden');
    slotCard.classList.add('hidden');
    confirmedCard.classList.add('hidden');

    if (sessionData.current_phase === 'WAITING_FOR_APPROVAL') {
        gateBanner.classList.remove('hidden');
    } else if (sessionData.current_phase === 'SLOT_SELECTION' && sessionData.plan.verified_candidate_slots) {
        slotCard.classList.remove('hidden');
        const slotsList = document.getElementById('candidate-slots-list');
        slotsList.innerHTML = '';
        sessionData.plan.verified_candidate_slots.forEach((slot, idx) => {
            const btn = document.createElement('button');
            btn.className = 'slot-btn';
            btn.onclick = () => handleSelectSlot(idx + 1);
            btn.innerHTML = `
                <span>Option ${idx + 1}: <strong>${slot}</strong></span>
                <i class="fa-solid fa-chevron-right"></i>
            `;
            slotsList.appendChild(btn);
        });
    } else if (sessionData.current_phase === 'COMPLETED' && sessionData.status === 'completed') {
        confirmedCard.classList.remove('hidden');
        document.getElementById('confirmed-slot-display').innerText = sessionData.plan.time_slot;
    }

    // Fetch and render Tool Execution Trace
    await fetchAndRenderTrace();
}

// Fetch tool trace logs
async function fetchAndRenderTrace() {
    if (!currentSessionId) return;

    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/trace`);
        const traceData = await res.json();

        const logsContainer = document.getElementById('tool-trace-logs');
        document.getElementById('tool-count-tag').innerText = `${traceData.tool_trace.length} tool calls`;
        
        if (traceData.tool_trace.length === 0) {
            logsContainer.innerHTML = '<div class="log-line text-muted">Awaiting plan approval to trigger tool calls...</div>';
            return;
        }

        logsContainer.innerHTML = '';
        traceData.tool_trace.forEach((trace, i) => {
            const div = document.createElement('div');
            div.className = 'log-line';
            div.innerHTML = `
                <span class="log-success">[SUCCESS] ${i + 1}. ${trace.tool}</span>
                <div class="log-reason">Reason: ${trace.reason}</div>
            `;
            logsContainer.appendChild(div);
        });
    } catch (err) {
        console.error('Error fetching trace:', err);
    }
}

// Lab 3 Document Export Modal
async function showFormatModal(fmt) {
    if (!currentSessionId) return;
    activeFormatTab = fmt || 'markdown';

    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/format?template_format=${activeFormatTab}`, {
            method: 'POST'
        });
        const data = await res.json();
        
        document.getElementById('format-modal').classList.remove('hidden');
        document.getElementById('formatted-content-area').value = data.content;
        
        const htmlPreview = document.getElementById('formatted-html-preview');
        const textArea = document.getElementById('formatted-content-area');
        
        if (activeFormatTab === 'html') {
            htmlPreview.innerHTML = data.content;
            htmlPreview.classList.remove('hidden');
            textArea.classList.add('hidden');
        } else {
            htmlPreview.classList.add('hidden');
            textArea.classList.remove('hidden');
        }
        
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`tab-${activeFormatTab}`).classList.add('active');
    } catch (err) {
        alert('Error formatting document: ' + err.message);
    }
}

function switchFormatTab(fmt) {
    showFormatModal(fmt);
}

function closeFormatModal() {
    document.getElementById('format-modal').classList.add('hidden');
}
