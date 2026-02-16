/**
 * Agent Dashboard - Frontend Application
 * Real-time monitoring and control interface with Auth, AI Chat, and Schedule Management
 */

// ===================================
// Configuration
// ===================================
const CONFIG = {
    WS_URL: `ws://${window.location.host}/ws`,
    API_BASE: '/api',
    RECONNECT_DELAY: 3000,
    MAX_RECONNECT_ATTEMPTS: 10,
    TOAST_DURATION: 4000,
    LOG_MAX_ENTRIES: 100,
    TOKEN_KEY: 'novaisabuilder_token',
    USER_KEY: 'novaisabuilder_user'
};

// ===================================
// State Management
// ===================================
const state = {
    // Auth
    currentUser: null,
    token: null,
    
    // Connection
    connected: false,
    reconnectAttempts: 0,
    ws: null,
    
    // Data
    logs: [],
    tasks: [],
    content: [],
    approvals: [],
    learnings: [],
    config: {},
    startTime: Date.now(),
    logFilter: 'all',
    
    // Chat
    chatMessages: [],
    pendingCommands: [],
    
    // UI
    isRegisterMode: false
};

// ===================================
// DOM Elements Cache
// ===================================
const elements = {
    // Pages
    loginPage: null,
    dashboardPage: null,
    
    // Login
    loginForm: null,
    registerForm: null,
    registerModal: null,
    loginError: null,
    registerError: null,
    
    // User Menu
    userMenuTrigger: null,
    userMenuDropdown: null,
    userDisplayName: null,
    userEmail: null,
    
    // Connection
    connectionStatus: null,
    connectionDot: null,
    connectionText: null,
    
    // Status
    agentStatusText: null,
    runningTime: null,
    browserStatus: null,
    dryRunStatus: null,
    pendingApprovals: null,
    
    // Chat
    chatContainer: null,
    chatInput: null,
    
    // Lists
    tasksTbody: null,
    tasksEmpty: null,
    contentList: null,
    contentEmpty: null,
    approvalList: null,
    approvalsEmpty: null,
    logContainer: null,
    learningsList: null,
    learningsEmpty: null,
    configList: null,
    
    // Toast
    toastContainer: null,
    
    // Filter
    logFilter: null,
    
    // Footer
    lastUpdated: null,
    
    // Schedule Modal
    scheduleModal: null
};

// ===================================
// Initialization
// ===================================
document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    initializeAuth();
    initializeEventListeners();
});

function cacheElements() {
    // Pages
    elements.loginPage = document.getElementById('login-page');
    elements.dashboardPage = document.getElementById('dashboard-page');
    
    // Login
    elements.loginForm = document.getElementById('login-form');
    elements.registerForm = document.getElementById('register-form');
    elements.registerModal = document.getElementById('register-modal');
    elements.loginError = document.getElementById('login-error');
    elements.registerError = document.getElementById('register-error');
    
    // User Menu
    elements.userMenuTrigger = document.getElementById('user-menu-trigger');
    elements.userMenuDropdown = document.getElementById('user-menu-dropdown');
    elements.userDisplayName = document.getElementById('user-display-name');
    elements.userEmail = document.getElementById('user-menu-email');
    
    // Connection
    elements.connectionStatus = document.getElementById('connection-status');
    elements.connectionDot = elements.connectionStatus?.querySelector('.connection-dot');
    elements.connectionText = elements.connectionStatus?.querySelector('.connection-text');
    
    // Status
    elements.agentStatusText = document.getElementById('agent-status-text');
    elements.runningTime = document.getElementById('running-time');
    elements.browserStatus = document.getElementById('browser-status');
    elements.dryRunStatus = document.getElementById('dry-run-status');
    elements.pendingApprovals = document.getElementById('pending-approvals');
    
    // Chat
    elements.chatContainer = document.getElementById('chat-container');
    elements.chatInput = document.getElementById('chat-input');
    
    // Lists
    elements.tasksTbody = document.getElementById('tasks-tbody');
    elements.tasksEmpty = document.getElementById('tasks-empty');
    elements.contentList = document.getElementById('content-list');
    elements.contentEmpty = document.getElementById('content-empty');
    elements.approvalList = document.getElementById('approval-list');
    elements.approvalsEmpty = document.getElementById('approvals-empty');
    elements.logContainer = document.getElementById('log-container');
    elements.learningsList = document.getElementById('learnings-list');
    elements.learningsEmpty = document.getElementById('learnings-empty');
    elements.configList = document.getElementById('config-list');
    
    // Toast
    elements.toastContainer = document.getElementById('toast-container');
    elements.logFilter = document.getElementById('log-filter');
    elements.lastUpdated = document.getElementById('last-updated');
    
    // Schedule Modal
    elements.scheduleModal = document.getElementById('schedule-modal');
}

function initializeEventListeners() {
    // Login form
    elements.loginForm?.addEventListener('submit', handleLogin);
    
    // Register form
    elements.registerForm?.addEventListener('submit', handleRegister);
    
    // Show register modal
    document.getElementById('show-register')?.addEventListener('click', (e) => {
        e.preventDefault();
        elements.registerModal?.classList.add('active');
    });
    
    // Hide register modal
    document.getElementById('show-login')?.addEventListener('click', (e) => {
        e.preventDefault();
        elements.registerModal?.classList.remove('active');
    });
    
    // User menu toggle
    elements.userMenuTrigger?.addEventListener('click', () => {
        elements.userMenuDropdown?.classList.toggle('active');
    });
    
    // Close user menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.user-menu')) {
            elements.userMenuDropdown?.classList.remove('active');
        }
    });
    
    // Logout
    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
    
    // Theme toggle
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        showToast('Theme toggle coming soon', 'info');
    });
    
    // Chat input
    elements.chatInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Schedule modal close on outside click
    elements.scheduleModal?.addEventListener('click', (e) => {
        if (e.target === elements.scheduleModal) {
            closeScheduleModal();
        }
    });
}

// ===================================
// Authentication
// ===================================
function initializeAuth() {
    const savedToken = localStorage.getItem(CONFIG.TOKEN_KEY);
    const savedUser = localStorage.getItem(CONFIG.USER_KEY);
    
    if (savedToken && savedUser) {
        try {
            state.token = JSON.parse(savedToken);
            state.currentUser = JSON.parse(savedUser);
            showDashboard();
        } catch (e) {
            clearAuth();
            showLogin();
        }
    } else {
        showLogin();
    }
}

function showLogin() {
    elements.loginPage.style.display = 'flex';
    elements.dashboardPage.style.display = 'none';
}

function showDashboard() {
    elements.loginPage.style.display = 'none';
    elements.dashboardPage.style.display = 'block';
    
    // Update user info
    if (state.currentUser) {
        elements.userDisplayName.textContent = state.currentUser.displayName || state.currentUser.email;
        elements.userEmail.textContent = state.currentUser.email;
    }
    
    // Connect WebSocket and fetch data
    connectWebSocket();
    fetchAllData();
    startRunningTimeUpdater();
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    elements.loginError.textContent = '';
    
    try {
        const response = await apiCall('/auth/login', 'POST', { email, password });
        
        state.token = {
            access: response.accessToken,
            refresh: response.refreshToken
        };
        state.currentUser = response.user;
        
        localStorage.setItem(CONFIG.TOKEN_KEY, JSON.stringify(state.token));
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(state.currentUser));
        
        showToast('Welcome back!', 'success');
        showDashboard();
    } catch (error) {
        elements.loginError.textContent = error.message || 'Invalid email or password';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const displayName = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    
    elements.registerError.textContent = '';
    
    try {
        const response = await apiCall('/auth/register', 'POST', { 
            displayName, 
            email, 
            password 
        });
        
        state.token = {
            access: response.accessToken,
            refresh: response.refreshToken
        };
        state.currentUser = response.user;
        
        localStorage.setItem(CONFIG.TOKEN_KEY, JSON.stringify(state.token));
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(state.currentUser));
        
        showToast('Account created successfully!', 'success');
        showDashboard();
    } catch (error) {
        elements.registerError.textContent = error.message || 'Registration failed';
    }
}

function handleLogout() {
    clearAuth();
    showLogin();
    showToast('You have been signed out', 'info');
}

function clearAuth() {
    state.token = null;
    state.currentUser = null;
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
    
    // Disconnect WebSocket
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }
}

// ===================================
// API Functions with Auth
// ===================================
async function apiCall(endpoint, method = 'GET', data = null, retry = true) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // Add auth header if we have a token
    if (state.token?.access) {
        options.headers['Authorization'] = `Bearer ${state.token.access}`;
    }
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${CONFIG.API_BASE}${endpoint}`, options);
        
        // Handle 401 - Unauthorized
        if (response.status === 401) {
            if (retry && state.token?.refresh) {
                // Try to refresh the token
                const refreshed = await refreshToken();
                if (refreshed) {
                    // Retry the original request
                    return apiCall(endpoint, method, data, false);
                }
            }
            // If refresh failed or no refresh token, logout
            handleLogout();
            throw new Error('Session expired. Please login again.');
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API call failed (${endpoint}):`, error);
        throw error;
    }
}

async function refreshToken() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refreshToken: state.token.refresh })
        });
        
        if (!response.ok) {
            return false;
        }
        
        const data = await response.json();
        state.token = {
            access: data.accessToken,
            refresh: data.refreshToken || state.token.refresh
        };
        
        localStorage.setItem(CONFIG.TOKEN_KEY, JSON.stringify(state.token));
        return true;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

async function fetchAllData() {
    try {
        await Promise.all([
            fetchStatus(),
            fetchTasks(),
            fetchContent(),
            fetchApprovals(),
            fetchLogs(),
            fetchLearnings(),
            fetchConfig()
        ]);
        updateLastUpdated();
    } catch (error) {
        console.error('Failed to fetch initial data:', error);
        showToast('Failed to load some data', 'warning');
    }
}

async function fetchStatus() {
    try {
        const data = await apiCall('/status');
        updateStatus(data);
    } catch (error) {
        updateStatus(getMockStatus());
    }
}

async function fetchTasks() {
    try {
        const data = await apiCall('/tasks');
        updateTasks(data);
    } catch (error) {
        updateTasks(getMockTasks());
    }
}

async function fetchContent() {
    try {
        const data = await apiCall('/content');
        updateContent(data);
    } catch (error) {
        updateContent(getMockContent());
    }
}

async function fetchApprovals() {
    try {
        const data = await apiCall('/approvals');
        updateApprovals(data);
    } catch (error) {
        updateApprovals(getMockApprovals());
    }
}

async function fetchLogs() {
    try {
        const data = await apiCall('/logs');
        state.logs = data.slice(-CONFIG.LOG_MAX_ENTRIES);
        renderLogs();
    } catch (error) {
        state.logs = getMockLogs();
        renderLogs();
    }
}

async function fetchLearnings() {
    try {
        const data = await apiCall('/learnings');
        updateLearnings(data);
    } catch (error) {
        updateLearnings(getMockLearnings());
    }
}

async function fetchConfig() {
    try {
        const data = await apiCall('/config');
        updateConfig(data);
    } catch (error) {
        updateConfig(getMockConfig());
    }
}

// ===================================
// WebSocket Connection
// ===================================
function connectWebSocket() {
    if (state.ws) {
        state.ws.close();
    }
    
    updateConnectionStatus('connecting');
    
    try {
        // Add auth to WebSocket URL
        const wsUrl = state.token?.access 
            ? `${CONFIG.WS_URL}?token=${encodeURIComponent(state.token.access)}`
            : CONFIG.WS_URL;
        
        state.ws = new WebSocket(wsUrl);
        
        state.ws.onopen = () => {
            console.log('WebSocket connected');
            state.connected = true;
            state.reconnectAttempts = 0;
            updateConnectionStatus('connected');
            showToast('Connected to server', 'success');
        };
        
        state.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            state.connected = false;
            updateConnectionStatus('disconnected');
            
            // Attempt reconnection
            if (state.reconnectAttempts < CONFIG.MAX_RECONNECT_ATTEMPTS && state.currentUser) {
                state.reconnectAttempts++;
                const delay = CONFIG.RECONNECT_DELAY * Math.min(state.reconnectAttempts, 5);
                console.log(`Reconnecting in ${delay}ms (attempt ${state.reconnectAttempts})`);
                setTimeout(connectWebSocket, delay);
            } else if (state.currentUser) {
                showToast('Connection lost. Please refresh the page.', 'error');
            }
        };
        
        state.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            showToast('Connection error', 'error');
        };
        
        state.ws.onmessage = (event) => {
            handleWebSocketMessage(event.data);
        };
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        updateConnectionStatus('disconnected');
    }
}

function handleWebSocketMessage(data) {
    try {
        const message = JSON.parse(data);
        
        switch (message.type) {
            case 'status':
                updateStatus(message.data);
                break;
            case 'log':
                addLogEntry(message.data);
                break;
            case 'task_update':
                updateTasks(message.data);
                break;
            case 'content_update':
                updateContent(message.data);
                break;
            case 'approval_update':
                updateApprovals(message.data);
                break;
            case 'learning':
                addLearning(message.data);
                break;
            case 'config_update':
                updateConfig(message.data);
                break;
            case 'chat':
                handleChatResponse(message.data);
                break;
            case 'toast':
                showToast(message.data.message, message.data.type || 'info');
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
        
        updateLastUpdated();
    } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
    }
}

function updateConnectionStatus(status) {
    if (!elements.connectionDot || !elements.connectionText) return;
    
    elements.connectionDot.className = 'connection-dot ' + status;
    
    const statusText = {
        connected: 'Connected',
        connecting: 'Connecting...',
        disconnected: 'Disconnected'
    };
    
    elements.connectionText.textContent = statusText[status] || status;
    
    const statusDot = document.querySelector('.status-dot');
    if (statusDot) {
        statusDot.className = 'status-dot ' + (status === 'connected' ? 'status-active' : 'status-inactive');
    }
    
    if (elements.agentStatusText) {
        elements.agentStatusText.textContent = status === 'connected' ? 'Active' : 'Offline';
    }
}

// ===================================
// AI Chat Functions
// ===================================
function sendChatMessage() {
    const message = elements.chatInput?.value.trim();
    if (!message) return;
    
    // Add user message to UI
    addChatMessage('user', message);
    elements.chatInput.value = '';
    
    // Send to API
    apiCall('/chat', 'POST', { message })
        .then(response => {
            if (response.proposal) {
                // AI proposed an action
                addChatMessage('ai', response.message, response.proposal);
            } else {
                addChatMessage('ai', response.message);
            }
        })
        .catch(error => {
            // For demo, simulate AI response
            simulateAIResponse(message);
        });
}

function sendSuggestion(text) {
    if (elements.chatInput) {
        elements.chatInput.value = text;
        sendChatMessage();
    }
}

function simulateAIResponse(message) {
    // Simulate AI thinking
    setTimeout(() => {
        const lowerMessage = message.toLowerCase();
        
        if (lowerMessage.includes('tweet') || lowerMessage.includes('post')) {
            const proposal = {
                type: 'create_tweet',
                description: 'Create and schedule a tweet',
                data: {
                    content: 'Exploring the fascinating world of AI and its impact on creative industries. The future is here! #AI #Future',
                    schedule: extractTimeFromMessage(message)
                }
            };
            addChatMessage('ai', `I'll create a tweet and schedule it for ${proposal.data.schedule}. Here's what I'll post:`, proposal);
        } else if (lowerMessage.includes('thread')) {
            const proposal = {
                type: 'create_thread',
                description: 'Create and schedule a thread',
                data: {
                    content: '5 productivity tips that changed my workflow...',
                    schedule: extractTimeFromMessage(message)
                }
            };
            addChatMessage('ai', `I'll create a thread and schedule it. Here's the draft:`, proposal);
        } else if (lowerMessage.includes('task') || lowerMessage.includes('pending')) {
            const taskCount = state.tasks.filter(t => t.enabled).length;
            addChatMessage('ai', `You have ${taskCount} active scheduled tasks. The next task will run at ${formatTime(state.tasks[0]?.nextRun)}. Would you like me to show you the details or create a new task?`);
        } else {
            addChatMessage('ai', "I can help you create content, schedule posts, and manage your agent. Try asking me to 'post a tweet about AI tomorrow at 9am' or 'schedule a thread for Monday'.");
        }
    }, 800);
}

function extractTimeFromMessage(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('tomorrow')) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        // Look for time
        const timeMatch = lowerMessage.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
        if (timeMatch) {
            let hours = parseInt(timeMatch[1]);
            const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
            
            if (timeMatch[3]) {
                if (timeMatch[3].toLowerCase() === 'pm' && hours < 12) hours += 12;
                if (timeMatch[3].toLowerCase() === 'am' && hours === 12) hours = 0;
            }
            
            tomorrow.setHours(hours, minutes, 0, 0);
        } else {
            tomorrow.setHours(9, 0, 0, 0);
        }
        
        return tomorrow.toISOString();
    }
    
    if (lowerMessage.includes('monday')) {
        return getNextDayOfWeek(1);
    }
    if (lowerMessage.includes('tuesday')) {
        return getNextDayOfWeek(2);
    }
    if (lowerMessage.includes('wednesday')) {
        return getNextDayOfWeek(3);
    }
    if (lowerMessage.includes('thursday')) {
        return getNextDayOfWeek(4);
    }
    if (lowerMessage.includes('friday')) {
        return getNextDayOfWeek(5);
    }
    
    // Default to 1 hour from now
    return new Date(Date.now() + 3600000).toISOString();
}

function getNextDayOfWeek(dayOfWeek) {
    const date = new Date();
    const currentDay = date.getDay();
    const diff = (dayOfWeek + 7 - currentDay) % 7 || 7;
    date.setDate(date.getDate() + diff);
    date.setHours(9, 0, 0, 0);
    return date.toISOString();
}

function addChatMessage(role, content, proposal = null) {
    const messageId = Date.now();
    
    state.chatMessages.push({
        id: messageId,
        role,
        content,
        proposal,
        timestamp: Date.now()
    });
    
    // Clear welcome message on first user message
    if (role === 'user' && state.chatMessages.length === 1) {
        elements.chatContainer.innerHTML = '';
    }
    
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message chat-message--${role}`;
    messageEl.id = `chat-msg-${messageId}`;
    
    if (role === 'user') {
        messageEl.innerHTML = `
            <div class="chat-bubble chat-bubble--user">
                <p>${escapeHtml(content)}</p>
            </div>
        `;
    } else {
        let proposalHtml = '';
        if (proposal) {
            proposalHtml = `
                <div class="chat-proposal">
                    <div class="proposal-preview">
                        <p>${escapeHtml(proposal.data?.content || proposal.description)}</p>
                    </div>
                    <div class="proposal-actions">
                        <button class="btn btn-success btn-sm" onclick="confirmProposal(${messageId})">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"/>
                            </svg>
                            Confirm
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="cancelProposal(${messageId})">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                            Cancel
                        </button>
                    </div>
                </div>
            `;
        }
        
        messageEl.innerHTML = `
            <div class="chat-bubble chat-bubble--ai">
                <div class="ai-avatar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M12 2v2m0 16v2M2 12h2m16 0h2"/>
                    </svg>
                </div>
                <div class="chat-content">
                    <p>${escapeHtml(content)}</p>
                    ${proposalHtml}
                </div>
            </div>
        `;
    }
    
    elements.chatContainer.appendChild(messageEl);
    
    // Scroll to bottom
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    
    // Animation
    messageEl.style.opacity = '0';
    messageEl.style.transform = 'translateY(10px)';
    requestAnimationFrame(() => {
        messageEl.style.transition = 'all 0.3s ease';
        messageEl.style.opacity = '1';
        messageEl.style.transform = 'translateY(0)';
    });
}

function confirmProposal(messageId) {
    const message = state.chatMessages.find(m => m.id === messageId);
    if (!message?.proposal) return;
    
    state.pendingCommands.push({
        messageId,
        proposal: message.proposal,
        timestamp: Date.now()
    });
    
    apiCall('/chat/confirm', 'POST', { proposal: message.proposal })
        .then(response => {
            showToast('Action confirmed!', 'success');
            updateProposalUI(messageId, 'confirmed');
        })
        .catch(error => {
            showToast(`Failed to execute: ${error.message}`, 'error');
        });
}

function cancelProposal(messageId) {
    const message = state.chatMessages.find(m => m.id === messageId);
    if (!message?.proposal) return;
    
    apiCall('/chat/cancel', 'POST', { proposalId: messageId })
        .then(() => {
            showToast('Action cancelled', 'info');
            updateProposalUI(messageId, 'cancelled');
        })
        .catch(() => {
            updateProposalUI(messageId, 'cancelled');
        });
}

function updateProposalUI(messageId, status) {
    const messageEl = document.getElementById(`chat-msg-${messageId}`);
    if (!messageEl) return;
    
    const actionsEl = messageEl.querySelector('.proposal-actions');
    if (actionsEl) {
        actionsEl.innerHTML = `<span class="proposal-status proposal-status--${status}">${status}</span>`;
    }
}

function handleChatResponse(data) {
    if (data.type === 'proposal') {
        addChatMessage('ai', data.message, data.proposal);
    } else {
        addChatMessage('ai', data.message);
    }
}

function clearChat() {
    state.chatMessages = [];
    state.pendingCommands = [];
    
    elements.chatContainer.innerHTML = `
        <div class="chat-welcome">
            <div class="chat-welcome-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M12 2v2m0 16v2M2 12h2m16 0h2"/>
                </svg>
            </div>
            <h3>How can I help you?</h3>
            <p>Ask me to create tasks, schedule posts, or manage your agent.</p>
            <div class="chat-suggestions">
                <button class="chat-suggestion" onclick="sendSuggestion('Post a tweet about AI tomorrow at 9am')">
                    "Post a tweet about AI tomorrow at 9am"
                </button>
                <button class="chat-suggestion" onclick="sendSuggestion('Schedule a thread about productivity for Monday')">
                    "Schedule a thread for Monday"
                </button>
                <button class="chat-suggestion" onclick="sendSuggestion('Show me my pending tasks')">
                    "Show my pending tasks"
                </button>
            </div>
        </div>
    `;
    
    showToast('Chat cleared', 'info');
}

// ===================================
// Schedule Management
// ===================================
function openScheduleModal(taskName) {
    const task = state.tasks.find(t => t.name === taskName);
    if (!task) return;
    
    document.getElementById('schedule-task-name').value = taskName;
    
    // Parse existing schedule
    const scheduleType = task.scheduleType || 'daily';
    document.getElementById('schedule-type').value = scheduleType;
    
    updateScheduleFields();
    
    // Populate fields based on schedule type
    if (task.scheduleInterval) {
        document.getElementById('schedule-interval').value = task.scheduleInterval;
    }
    
    if (task.scheduleTime) {
        document.getElementById('schedule-time').value = task.scheduleTime;
        document.getElementById('schedule-weekly-time').value = task.scheduleTime;
    }
    
    if (task.scheduleDays) {
        task.scheduleDays.forEach(day => {
            const checkbox = document.getElementById(`day-${day.toLowerCase()}`);
            if (checkbox) checkbox.checked = true;
        });
    }
    
    if (task.scheduleDatetime) {
        document.getElementById('schedule-datetime').value = task.scheduleDatetime;
    }
    
    elements.scheduleModal.classList.add('active');
}

function closeScheduleModal() {
    elements.scheduleModal.classList.remove('active');
}

function updateScheduleFields() {
    const type = document.getElementById('schedule-type').value;
    
    // Hide all fields
    document.querySelectorAll('.schedule-fields').forEach(el => {
        el.style.display = 'none';
    });
    
    // Show relevant fields
    switch (type) {
        case 'once':
            document.getElementById('once-fields').style.display = 'block';
            // Set default datetime to now + 1 hour
            if (!document.getElementById('schedule-datetime').value) {
                const defaultDate = new Date(Date.now() + 3600000);
                document.getElementById('schedule-datetime').value = defaultDate.toISOString().slice(0, 16);
            }
            break;
        case 'interval':
            document.getElementById('interval-fields').style.display = 'block';
            break;
        case 'daily':
            document.getElementById('time-fields').style.display = 'block';
            break;
        case 'weekly':
            document.getElementById('weekly-fields').style.display = 'block';
            break;
    }
}

async function saveSchedule() {
    const taskName = document.getElementById('schedule-task-name').value;
    const type = document.getElementById('schedule-type').value;
    
    const scheduleData = {
        type,
        taskName
    };
    
    switch (type) {
        case 'once':
            scheduleData.datetime = document.getElementById('schedule-datetime').value;
            break;
        case 'interval':
            scheduleData.interval = parseInt(document.getElementById('schedule-interval').value);
            break;
        case 'daily':
            scheduleData.time = document.getElementById('schedule-time').value;
            break;
        case 'weekly':
            scheduleData.time = document.getElementById('schedule-weekly-time').value;
            scheduleData.days = [];
            document.querySelectorAll('.day-checkbox input:checked').forEach(cb => {
                scheduleData.days.push(cb.value);
            });
            break;
    }
    
    try {
        await apiCall(`/tasks/${encodeURIComponent(taskName)}/schedule`, 'PUT', scheduleData);
        showToast('Schedule updated', 'success');
        closeScheduleModal();
        refreshTasks();
    } catch (error) {
        showToast(`Failed to update schedule: ${error.message}`, 'error');
    }
}

function formatScheduleDescription(task) {
    if (!task.enabled) {
        return 'Disabled';
    }
    
    if (task.scheduleDescription) {
        return task.scheduleDescription;
    }
    
    const type = task.scheduleType || 'daily';
    
    switch (type) {
        case 'once':
            const date = new Date(task.scheduleDatetime);
            return `Once on ${date.toLocaleDateString()} at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        case 'interval':
            return `Every ${task.scheduleInterval} minutes`;
        case 'daily':
            return `Daily at ${formatTimeFromString(task.scheduleTime)}`;
        case 'weekly':
            const days = (task.scheduleDays || []).map(d => d.charAt(0).toUpperCase() + d.slice(1, 3)).join('/');
            return `${days} at ${formatTimeFromString(task.scheduleTime)}`;
        default:
            return task.cron || 'Manual';
    }
}

function formatTimeFromString(timeStr) {
    if (!timeStr) return '--';
    const [hours, minutes] = timeStr.split(':');
    const date = new Date();
    date.setHours(parseInt(hours), parseInt(minutes));
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// ===================================
// Action Functions
// ===================================
async function runTask(name) {
    try {
        showToast(`Running task: ${name}`, 'info');
        await apiCall(`/tasks/${encodeURIComponent(name)}/run`, 'POST');
        showToast(`Task ${name} started`, 'success');
    } catch (error) {
        showToast(`Failed to run task: ${error.message}`, 'error');
    }
}

async function toggleTask(name, enable) {
    try {
        await apiCall(`/tasks/${encodeURIComponent(name)}/toggle`, 'POST', { enabled: enable });
        showToast(`Task ${name} ${enable ? 'enabled' : 'disabled'}`, 'success');
        refreshTasks();
    } catch (error) {
        showToast(`Failed to toggle task: ${error.message}`, 'error');
    }
}

async function approveAction(id) {
    try {
        await apiCall(`/approvals/${id}/approve`, 'POST');
        showToast('Action approved', 'success');
        refreshApprovals();
    } catch (error) {
        showToast(`Failed to approve: ${error.message}`, 'error');
    }
}

async function rejectAction(id) {
    try {
        await apiCall(`/approvals/${id}/reject`, 'POST');
        showToast('Action rejected', 'warning');
        refreshApprovals();
    } catch (error) {
        showToast(`Failed to reject: ${error.message}`, 'error');
    }
}

async function approveAll() {
    const pendingCount = state.approvals.length;
    if (pendingCount === 0) {
        showToast('No pending approvals', 'info');
        return;
    }
    
    if (!confirm(`Approve all ${pendingCount} pending items?`)) return;
    
    try {
        await apiCall('/approvals/approve-all', 'POST');
        showToast(`${pendingCount} actions approved`, 'success');
        refreshApprovals();
    } catch (error) {
        showToast(`Failed to approve all: ${error.message}`, 'error');
    }
}

async function postContent(id) {
    try {
        showToast('Posting content...', 'info');
        await apiCall(`/content/${id}/post`, 'POST');
        showToast('Content posted successfully', 'success');
        refreshContent();
    } catch (error) {
        showToast(`Failed to post content: ${error.message}`, 'error');
    }
}

async function deleteContent(id) {
    if (!confirm('Delete this content?')) return;
    
    try {
        await apiCall(`/content/${id}`, 'DELETE');
        showToast('Content deleted', 'success');
        refreshContent();
    } catch (error) {
        showToast(`Failed to delete content: ${error.message}`, 'error');
    }
}

async function toggleConfig(key, value) {
    try {
        await apiCall(`/config/${key}`, 'PUT', { value });
        showToast(`${key} updated`, 'success');
    } catch (error) {
        showToast(`Failed to update config: ${error.message}`, 'error');
    }
}

// ===================================
// Refresh Functions
// ===================================
function refreshTasks() {
    fetchTasks();
}

function refreshContent() {
    fetchContent();
}

function refreshApprovals() {
    fetchApprovals();
}

function clearLogs() {
    state.logs = [];
    renderLogs();
    showToast('Logs cleared', 'info');
}

function filterLogs() {
    state.logFilter = elements.logFilter?.value || 'all';
    renderLogs();
}

// ===================================
// Update Functions
// ===================================
function updateStatus(data) {
    if (elements.runningTime && data.startTime) {
        state.startTime = data.startTime;
    }
    
    if (elements.browserStatus) {
        elements.browserStatus.textContent = data.browserStatus || 'Idle';
    }
    
    if (elements.dryRunStatus) {
        elements.dryRunStatus.textContent = data.dryRun ? 'On' : 'Off';
        elements.dryRunStatus.style.color = data.dryRun ? 'var(--warning)' : 'var(--text-primary)';
    }
    
    if (elements.pendingApprovals) {
        const count = data.pendingApprovals || state.approvals.length;
        elements.pendingApprovals.textContent = count;
    }
}

function updateTasks(tasks) {
    state.tasks = tasks || [];
    
    if (!elements.tasksTbody || !elements.tasksEmpty) return;
    
    if (state.tasks.length === 0) {
        elements.tasksTbody.innerHTML = '';
        elements.tasksEmpty.style.display = 'flex';
        return;
    }
    
    elements.tasksEmpty.style.display = 'none';
    
    elements.tasksTbody.innerHTML = state.tasks.map(task => `
        <tr class="${task.enabled ? '' : 'task-disabled'}">
            <td data-label="Task">
                <span class="task-name">${escapeHtml(task.name)}</span>
            </td>
            <td data-label="Schedule">
                <span class="task-schedule">${escapeHtml(formatScheduleDescription(task))}</span>
            </td>
            <td data-label="Last Run">
                <span class="task-time">${formatTime(task.lastRun)}</span>
            </td>
            <td data-label="Next Run">
                <span class="task-time">${formatTime(task.nextRun)}</span>
            </td>
            <td data-label="Actions">
                <div class="task-actions">
                    <label class="toggle" title="${task.enabled ? 'Disable' : 'Enable'}">
                        <input type="checkbox" ${task.enabled ? 'checked' : ''} 
                               onchange="toggleTask('${escapeHtml(task.name)}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                    <button class="btn btn-sm btn-ghost" onclick="runTask('${escapeHtml(task.name)}')" 
                            title="Run now">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg>
                    </button>
                    <button class="btn btn-sm btn-ghost" onclick="openScheduleModal('${escapeHtml(task.name)}')" 
                            title="Edit schedule">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2"/>
                            <path d="M16 2v4M8 2v4M3 10h18"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function updateContent(content) {
    state.content = content || [];
    
    if (!elements.contentList || !elements.contentEmpty) return;
    
    if (state.content.length === 0) {
        elements.contentList.innerHTML = '';
        elements.contentEmpty.style.display = 'flex';
        return;
    }
    
    elements.contentEmpty.style.display = 'none';
    
    elements.contentList.innerHTML = state.content.map(item => `
        <div class="content-item">
            <div class="content-item-header">
                <span class="content-type ${item.status}">${item.status}</span>
                ${item.scheduledFor ? `<span class="content-scheduled-time">${formatTime(item.scheduledFor)}</span>` : ''}
            </div>
            <div class="content-preview">${escapeHtml(item.preview || item.content || 'No preview')}</div>
            <div class="content-actions">
                ${item.status !== 'published' ? `
                    <button class="btn btn-sm btn-success" onclick="postContent('${item.id}')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="22" y1="2" x2="11" y2="13"/>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                        </svg>
                        Post Now
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-danger" onclick="deleteContent('${item.id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

function updateApprovals(approvals) {
    state.approvals = approvals || [];
    
    if (elements.pendingApprovals) {
        elements.pendingApprovals.textContent = state.approvals.length;
    }
    
    if (!elements.approvalList || !elements.approvalsEmpty) return;
    
    if (state.approvals.length === 0) {
        elements.approvalList.innerHTML = '';
        elements.approvalsEmpty.style.display = 'flex';
        return;
    }
    
    elements.approvalsEmpty.style.display = 'none';
    
    elements.approvalList.innerHTML = state.approvals.map(item => `
        <div class="approval-item">
            <div class="approval-header">
                <span class="approval-type">${escapeHtml(item.type || 'Action')}</span>
                <span class="approval-time">${formatTime(item.createdAt)}</span>
            </div>
            <div class="approval-content">${escapeHtml(item.description || item.content || 'No description')}</div>
            <div class="approval-actions">
                <button class="btn btn-sm btn-success" onclick="approveAction('${item.id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    Approve
                </button>
                <button class="btn btn-sm btn-danger" onclick="rejectAction('${item.id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                    Reject
                </button>
            </div>
        </div>
    `).join('');
}

function updateLearnings(learnings) {
    state.learnings = learnings || [];
    
    if (!elements.learningsList || !elements.learningsEmpty) return;
    
    if (state.learnings.length === 0) {
        elements.learningsList.innerHTML = '';
        elements.learningsEmpty.style.display = 'flex';
        return;
    }
    
    elements.learningsEmpty.style.display = 'none';
    
    elements.learningsList.innerHTML = state.learnings.map(item => `
        <div class="learning-item">
            <div class="learning-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
            </div>
            <div class="learning-content">
                <div class="learning-text">${escapeHtml(item.insight || item.text)}</div>
                <div class="learning-meta">${formatTime(item.timestamp)} ${item.experiment ? `• ${escapeHtml(item.experiment)}` : ''}</div>
            </div>
        </div>
    `).join('');
}

function updateConfig(config) {
    state.config = config || {};
    
    if (!elements.configList) return;
    
    const configItems = Object.entries(state.config).map(([key, item]) => {
        const isBoolean = typeof item.value === 'boolean';
        
        return `
            <div class="config-item">
                <div class="config-label">
                    <span class="config-name">${escapeHtml(item.label || key)}</span>
                    ${item.description ? `<span class="config-desc">${escapeHtml(item.description)}</span>` : ''}
                </div>
                ${isBoolean ? `
                    <label class="toggle">
                        <input type="checkbox" ${item.value ? 'checked' : ''} 
                               onchange="toggleConfig('${key}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                ` : `
                    <span class="config-value">${escapeHtml(String(item.value))}</span>
                `}
            </div>
        `;
    });
    
    elements.configList.innerHTML = configItems.join('');
}

function addLogEntry(log) {
    state.logs.push(log);
    
    if (state.logs.length > CONFIG.LOG_MAX_ENTRIES) {
        state.logs = state.logs.slice(-CONFIG.LOG_MAX_ENTRIES);
    }
    
    if (state.logFilter === 'all' || log.level === state.logFilter) {
        appendLogEntry(log);
    }
}

function addLearning(learning) {
    state.learnings.unshift(learning);
    
    if (state.learnings.length > 10) {
        state.learnings = state.learnings.slice(0, 10);
    }
    
    updateLearnings(state.learnings);
}

// ===================================
// Render Functions
// ===================================
function renderLogs() {
    if (!elements.logContainer) return;
    
    const filteredLogs = state.logFilter === 'all' 
        ? state.logs 
        : state.logs.filter(log => log.level === state.logFilter);
    
    elements.logContainer.innerHTML = filteredLogs.map(log => `
        <div class="log-entry" data-level="${log.level}">
            <span class="log-time">${formatTime(log.timestamp)}</span>
            <span class="log-level ${log.level}">${log.level}</span>
            <span class="log-message">${escapeHtml(log.message)}</span>
        </div>
    `).join('');
    
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
}

function appendLogEntry(log) {
    if (!elements.logContainer) return;
    
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.dataset.level = log.level;
    entry.innerHTML = `
        <span class="log-time">${formatTime(log.timestamp)}</span>
        <span class="log-level ${log.level}">${log.level}</span>
        <span class="log-message">${escapeHtml(log.message)}</span>
    `;
    
    elements.logContainer.appendChild(entry);
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
}

// ===================================
// Toast Notifications
// ===================================
function showToast(message, type = 'info') {
    if (!elements.toastContainer) return;
    
    const icons = {
        success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>`,
        error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>`,
        warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>`,
        info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>`
    };
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <span class="toast-icon ${type}">${icons[type] || icons.info}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, CONFIG.TOAST_DURATION);
}

// ===================================
// Utility Functions
// ===================================
function formatTime(timestamp) {
    if (!timestamp) return '--';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) {
        return 'Just now';
    }
    
    if (diff < 3600000) {
        const mins = Math.floor(diff / 60000);
        return `${mins}m ago`;
    }
    
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }
    
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateLastUpdated() {
    if (elements.lastUpdated) {
        elements.lastUpdated.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    }
}

function startRunningTimeUpdater() {
    setInterval(() => {
        if (!elements.runningTime) return;
        
        const diff = Date.now() - state.startTime;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        
        elements.runningTime.textContent = `${hours}h ${minutes}m`;
    }, 1000);
}

// ===================================
// Mock Data (for development/demo)
// ===================================
function getMockStatus() {
    return {
        startTime: Date.now() - 3600000 * 2,
        browserStatus: 'Active',
        dryRun: true,
        pendingApprovals: 3
    };
}

function getMockTasks() {
    return [
        { 
            name: 'content_generation', 
            scheduleType: 'interval',
            scheduleInterval: 240,
            scheduleDescription: 'Every 4 hours',
            lastRun: Date.now() - 3600000, 
            nextRun: Date.now() + 3600000 * 3, 
            enabled: true 
        },
        { 
            name: 'analytics_fetch', 
            scheduleType: 'daily',
            scheduleTime: '09:00',
            scheduleDescription: 'Daily at 9:00 AM',
            lastRun: Date.now() - 86400000, 
            nextRun: Date.now() + 3600000 * 12, 
            enabled: true 
        },
        { 
            name: 'cleanup_logs', 
            scheduleType: 'weekly',
            scheduleTime: '00:00',
            scheduleDays: ['sun'],
            scheduleDescription: 'Sun at 12:00 AM',
            lastRun: Date.now() - 604800000, 
            nextRun: Date.now() + 259200000, 
            enabled: true 
        },
        { 
            name: 'email_digest', 
            scheduleType: 'weekly',
            scheduleTime: '18:00',
            scheduleDays: ['mon', 'tue', 'wed', 'thu', 'fri'],
            scheduleDescription: 'Mon/Tue/Wed/Thu/Fri at 6:00 PM',
            lastRun: null, 
            nextRun: null, 
            enabled: false 
        }
    ];
}

function getMockContent() {
    return [
        { id: '1', status: 'draft', preview: 'Exploring the intersection of AI and creative writing. Thread about how LLMs are changing content creation workflows...', scheduledFor: null },
        { id: '2', status: 'scheduled', preview: '5 productivity tips for remote workers that actually work. Based on my experience over the past year...', scheduledFor: Date.now() + 3600000 * 5 },
        { id: '3', status: 'draft', preview: 'A deep dive into semantic search and vector databases. Why traditional search is becoming obsolete...', scheduledFor: null }
    ];
}

function getMockApprovals() {
    return [
        { id: 'a1', type: 'Tweet', content: 'Just shipped a new feature! Check it out and let me know what you think 🚀', createdAt: Date.now() - 1800000 },
        { id: 'a2', type: 'Reply', content: 'Thanks for the feedback! We are working on adding that feature in the next release.', createdAt: Date.now() - 3600000 },
        { id: 'a3', type: 'Follow', content: 'Follow @techfounder - interesting insights on startup growth', createdAt: Date.now() - 7200000 }
    ];
}

function getMockLogs() {
    return [
        { level: 'info', message: 'Agent started successfully', timestamp: Date.now() - 7200000 },
        { level: 'success', message: 'Connected to browser instance', timestamp: Date.now() - 7100000 },
        { level: 'info', message: 'Loading scheduled tasks', timestamp: Date.now() - 7000000 },
        { level: 'warning', message: 'Rate limit approaching for API endpoint', timestamp: Date.now() - 3600000 },
        { level: 'success', message: 'Content generated: thread about AI productivity', timestamp: Date.now() - 1800000 },
        { level: 'info', message: 'Waiting for approval on 3 items', timestamp: Date.now() - 900000 }
    ];
}

function getMockLearnings() {
    return [
        { insight: 'Posts with questions get 2.3x more engagement than statements', experiment: 'tweet_formatting', timestamp: Date.now() - 86400000 },
        { insight: 'Optimal posting time for audience is 9AM-11AM on weekdays', experiment: 'posting_schedule', timestamp: Date.now() - 172800000 },
        { insight: 'Thread length of 5-7 tweets performs best for retention', experiment: 'thread_length', timestamp: Date.now() - 259200000 }
    ];
}

function getMockConfig() {
    return {
        dryRun: { label: 'Dry Run Mode', value: true, description: 'Preview actions without executing' },
        autoApprove: { label: 'Auto-Approve Safe Actions', value: false, description: 'Automatically approve low-risk actions' },
        notifications: { label: 'Email Notifications', value: true, description: 'Receive email alerts for important events' },
        maxPosts: { label: 'Max Posts Per Day', value: 10, description: 'Daily posting limit' }
    };
}

// ===================================
// Export for global access (used in HTML onclick handlers)
// ===================================
window.runTask = runTask;
window.toggleTask = toggleTask;
window.approveAction = approveAction;
window.rejectAction = rejectAction;
window.approveAll = approveAll;
window.postContent = postContent;
window.deleteContent = deleteContent;
window.toggleConfig = toggleConfig;
window.refreshTasks = refreshTasks;
window.clearLogs = clearLogs;
window.filterLogs = filterLogs;
window.clearChat = clearChat;
window.sendChatMessage = sendChatMessage;
window.sendSuggestion = sendSuggestion;
window.confirmProposal = confirmProposal;
window.cancelProposal = cancelProposal;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.updateScheduleFields = updateScheduleFields;
window.saveSchedule = saveSchedule;
