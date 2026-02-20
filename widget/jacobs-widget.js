/**
 * Jane Jacobs Chatbot Widget
 * Embeddable chat widget for websites
 *
 * Usage:
 * <script src="jacobs-widget.js" data-api-url="http://localhost:8000"></script>
 */

(function() {
    'use strict';

    // Configuration
    const script = document.currentScript;
    const API_URL = script.getAttribute('data-api-url') || 'http://localhost:8000';

    let conversationId = null;
    let isOpen = false;
    let isTyping = false;

    // Conversation starters
    const STARTERS = [
        "What do you think about remote work killing downtowns?",
        "Are 15-minute cities a real idea or just branding?",
        "What would you say to a city planner today?",
        "What are cities still getting wrong?"
    ];

    // Create widget HTML
    function createWidget() {
        const container = document.createElement('div');
        container.id = 'jane-jacobs-widget';
        container.innerHTML = `
            <div id="jj-trigger" class="jj-trigger">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="7" height="7"></rect>
                    <rect x="14" y="3" width="7" height="7"></rect>
                    <rect x="14" y="14" width="7" height="7"></rect>
                    <rect x="3" y="14" width="7" height="7"></rect>
                </svg>
            </div>

            <div id="jj-chat-window" class="jj-chat-window jj-hidden">
                <div class="jj-header">
                    <div class="jj-header-content">
                        <h3>Jane Jacobs</h3>
                        <p class="jj-subtitle">(1916 – )</p>
                        <p class="jj-tagline">Ask her anything about cities, neighborhoods, or what we keep getting wrong</p>
                    </div>
                    <button id="jj-close" class="jj-close-btn">&times;</button>
                </div>

                <div id="jj-messages" class="jj-messages">
                    <div class="jj-starters">
                        ${STARTERS.map((starter, i) =>
                            `<button class="jj-starter-btn" data-index="${i}">${starter}</button>`
                        ).join('')}
                    </div>
                </div>

                <div class="jj-input-container">
                    <input
                        type="text"
                        id="jj-input"
                        class="jj-input"
                        placeholder="Ask Jane a question..."
                        disabled
                    />
                    <button id="jj-send" class="jj-send-btn" disabled>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(container);
        attachEventListeners();
    }

    // Attach event listeners
    function attachEventListeners() {
        const trigger = document.getElementById('jj-trigger');
        const closeBtn = document.getElementById('jj-close');
        const sendBtn = document.getElementById('jj-send');
        const input = document.getElementById('jj-input');

        trigger.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', closeChat);
        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Starter buttons
        document.querySelectorAll('.jj-starter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const starter = STARTERS[parseInt(btn.getAttribute('data-index'))];
                input.value = starter;
                sendMessage();
            });
        });
    }

    // Toggle chat window
    function toggleChat() {
        const chatWindow = document.getElementById('jj-chat-window');
        const input = document.getElementById('jj-input');
        const sendBtn = document.getElementById('jj-send');

        if (isOpen) {
            closeChat();
        } else {
            chatWindow.classList.remove('jj-hidden');
            isOpen = true;
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    }

    // Close chat
    function closeChat() {
        const chatWindow = document.getElementById('jj-chat-window');
        chatWindow.classList.add('jj-hidden');
        isOpen = false;
    }

    // Send message
    async function sendMessage() {
        const input = document.getElementById('jj-input');
        const message = input.value.trim();

        if (!message || isTyping) return;

        // Clear starters if this is first message
        const starters = document.querySelector('.jj-starters');
        if (starters) {
            starters.remove();
        }

        // Add user message
        addMessage(message, 'user');
        input.value = '';
        input.disabled = true;

        // Show typing indicator
        showTyping();

        try {
            // Call API
            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId
                })
            });

            if (!response.ok) {
                throw new Error('API request failed');
            }

            const data = await response.json();
            conversationId = data.conversation_id;

            // Remove typing indicator
            removeTyping();

            // Add assistant response with typewriter effect
            await addMessageTypewriter(data.response, 'assistant', data.sources);

        } catch (error) {
            console.error('Error sending message:', error);
            removeTyping();
            addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
        } finally {
            input.disabled = false;
            input.focus();
        }
    }

    // Add message to chat
    function addMessage(text, role, sources = null) {
        const messagesDiv = document.getElementById('jj-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `jj-message jj-message-${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'jj-message-content';
        contentDiv.textContent = text;

        messageDiv.appendChild(contentDiv);

        // Add sources if available
        if (sources && sources.length > 0 && role === 'assistant') {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'jj-sources';

            sources.forEach(source => {
                const sourceSpan = document.createElement('span');
                sourceSpan.className = 'jj-source';
                sourceSpan.textContent = `${source.title}, ${source.year}`;
                sourcesDiv.appendChild(sourceSpan);
            });

            messageDiv.appendChild(sourcesDiv);
        }

        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // Add message with typewriter effect
    function addMessageTypewriter(text, role, sources = null) {
        return new Promise((resolve) => {
            const messagesDiv = document.getElementById('jj-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `jj-message jj-message-${role}`;

            const contentDiv = document.createElement('div');
            contentDiv.className = 'jj-message-content';

            messageDiv.appendChild(contentDiv);
            messagesDiv.appendChild(messageDiv);

            let i = 0;
            const baseSpeed = 12; // Base ms per character

            function typeChar() {
                if (i < text.length) {
                    const char = text.charAt(i);
                    contentDiv.textContent += char;
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    i++;

                    // Variable speed for more natural typing
                    let speed = baseSpeed;
                    if (char === '.' || char === '!' || char === '?') {
                        speed = baseSpeed * 15; // Pause at end of sentences
                    } else if (char === ',' || char === ';' || char === ':') {
                        speed = baseSpeed * 8; // Pause at punctuation
                    } else if (char === ' ') {
                        speed = baseSpeed * 1.2; // Slight pause at spaces
                    } else {
                        // Random variation for natural feel
                        speed = baseSpeed + (Math.random() * 8 - 4);
                    }

                    setTimeout(typeChar, Math.max(speed, 5));
                } else {
                    // Add sources after typing completes
                    if (sources && sources.length > 0) {
                        const sourcesDiv = document.createElement('div');
                        sourcesDiv.className = 'jj-sources';

                        sources.forEach(source => {
                            const sourceSpan = document.createElement('span');
                            sourceSpan.className = 'jj-source';
                            sourceSpan.textContent = `${source.title}, ${source.year}`;
                            sourcesDiv.appendChild(sourceSpan);
                        });

                        messageDiv.appendChild(sourcesDiv);
                    }
                    resolve();
                }
            }

            typeChar();
        });
    }

    // Show typing indicator
    function showTyping() {
        isTyping = true;
        const messagesDiv = document.getElementById('jj-messages');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'jj-typing';
        typingDiv.className = 'jj-message jj-message-assistant';
        typingDiv.innerHTML = '<div class="jj-typing-indicator"><span></span><span></span><span></span></div>';
        messagesDiv.appendChild(typingDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // Remove typing indicator
    function removeTyping() {
        isTyping = false;
        const typingDiv = document.getElementById('jj-typing');
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createWidget);
    } else {
        createWidget();
    }
})();
