/* Hybrid AI Council - WebSocket Client */

let ws = null;
let connectionId = null;
let currentStreamingMessage = null;
let streamingContent = '';
let currentPhase = 0;

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function(event) {
        document.getElementById('status').innerHTML = '🟢 Connected to AI Council';
        document.getElementById('statusContainer').style.borderColor = 'var(--accent-green)';
        resetPhases();
    };
    
    ws.onmessage = function(event) {
        const response = JSON.parse(event.data);
        displayMessage(response);
    };
    
    ws.onclose = function(event) {
        document.getElementById('status').innerHTML = '🔴 Disconnected';
        document.getElementById('statusContainer').style.borderColor = 'var(--accent-red)';
        setTimeout(connect, 3000); // Reconnect after 3 seconds
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        document.getElementById('status').innerHTML = '❌ Connection Error';
        document.getElementById('statusContainer').style.borderColor = 'var(--accent-red)';
    };
}

function resetPhases() {
    currentPhase = 0;
    const phases = ['phase-1', 'phase-2', 'phase-3'];
    phases.forEach(id => {
        document.getElementById(id).classList.remove('active');
    });
}

function activatePhase(phaseNum) {
    if (phaseNum > currentPhase) {
        currentPhase = phaseNum;
        const phaseId = `phase-${phaseNum}`;
        document.getElementById(phaseId).classList.add('active');
    }
}

function updatePhaseFromContent(content) {
    if (content.includes('Phase 1') || content.includes('concurrent') || content.includes('analyzing concurrently')) {
        activatePhase(1);
    } else if (content.includes('Phase 2') || content.includes('critique') || content.includes('critiquing')) {
        activatePhase(2);
    } else if (content.includes('Phase 3') || content.includes('synthesis') || content.includes('synthesizing')) {
        activatePhase(3);
    }
}

function displayMessage(response) {
    const messagesDiv = document.getElementById('messages');
    
    if (response.type === 'partial') {
        // Handle streaming tokens
        if (!currentStreamingMessage) {
            // Create new streaming message container
            currentStreamingMessage = document.createElement('div');
            currentStreamingMessage.className = 'message streaming';
            currentStreamingMessage.innerHTML = `<strong>AI COUNCIL:</strong> <span class="streaming-content"></span>`;
            messagesDiv.appendChild(currentStreamingMessage);
            streamingContent = '';
        }
        
        // Append token to streaming content
        streamingContent += response.content;
        const contentSpan = currentStreamingMessage.querySelector('.streaming-content');
        contentSpan.textContent = streamingContent;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
    } else if (response.type === 'final') {
        // Complete the streaming message
        if (currentStreamingMessage) {
            currentStreamingMessage.className = 'message final';
            const contentSpan = currentStreamingMessage.querySelector('.streaming-content');
            contentSpan.textContent = response.content;
            
            // Add metadata
            if (response.metadata && Object.keys(response.metadata).length > 0) {
                const metadataDiv = document.createElement('div');
                metadataDiv.className = 'metadata';
                metadataDiv.innerHTML = `Time: ${response.processing_time.toFixed(1)}s | ` + 
                                       `Agents: ${response.metadata.agents_participated ? response.metadata.agents_participated.join(', ') : 'unknown'}`;
                currentStreamingMessage.appendChild(metadataDiv);
            }
            
            currentStreamingMessage = null;
            streamingContent = '';
        } else {
            // Fallback for non-streaming final response
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message final';
            messageDiv.innerHTML = `<strong>FINAL:</strong> ${response.content}`;
            messagesDiv.appendChild(messageDiv);
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
    } else {
        // Handle status, error, and other message types
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${response.type}`;
        
        // Update phase indicators for status messages
        if (response.type === 'status') {
            updatePhaseFromContent(response.content);
        }
        
        let content = `<strong>${response.type.toUpperCase()}:</strong> ${response.content}`;
        
        if (response.phase && response.type === 'status') {
            content += `<div class="metadata">Phase: ${response.phase}`;
            if (response.processing_time) {
                content += ` | Time: ${response.processing_time.toFixed(1)}s`;
            }
            if (response.metadata && response.metadata.agent) {
                content += ` | Agent: ${response.metadata.agent}`;
            }
            content += `</div>`;
        }
        
        messageDiv.innerHTML = content;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    // Store connection info
    if (response.type === 'status' && response.request_id.startsWith('connection_')) {
        connectionId = response.request_id.replace('connection_', '');
        document.getElementById('connectionId').textContent = connectionId.substring(0, 8) + '...';
    }
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || !ws || ws.readyState !== WebSocket.OPEN) {
        return;
    }
    
    // Reset phases for new deliberation
    resetPhases();
    
    // Display user message
    const messagesDiv = document.getElementById('messages');
    const userDiv = document.createElement('div');
    userDiv.className = 'message user';
    userDiv.innerHTML = `<strong>YOU:</strong> ${message}`;
    messagesDiv.appendChild(userDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Send to server
    ws.send(JSON.stringify({
        message: message,
        conversation_id: connectionId || 'test_conversation'
    }));
    
    input.value = '';
    
    // Disable send button temporarily
    const sendButton = document.getElementById('sendButton');
    sendButton.disabled = true;
    sendButton.textContent = 'Processing...';
    
    setTimeout(() => {
        sendButton.disabled = false;
        sendButton.textContent = 'Send Message';
    }, 3000);
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Connect on page load
connect();