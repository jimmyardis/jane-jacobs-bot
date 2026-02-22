/**
 * Historical Figure Chatbot Widget
 * Embeddable chat widget with persona configuration support
 *
 * Usage:
 * <script src="jacobs-widget.js"
 *         data-api-url="http://localhost:8000"
 *         data-persona-id="jane-jacobs"></script>
 */

(function() {
    'use strict';

    // Configuration from script tag
    const script = document.currentScript;
    const API_URL = script.getAttribute('data-api-url') || 'http://localhost:8000';
    const PERSONA_ID = script.getAttribute('data-persona-id') || 'jane-jacobs';

    let conversationId = null;
    let isOpen = false;
    let isTyping = false;
    let personaConfig = null;

    // Load persona configuration and initialize widget
    async function init() {
        try {
            personaConfig = await loadPersonaConfig();
            applyPersonaTheme(personaConfig);
            createWidget(personaConfig);
        } catch (error) {
            console.error('Failed to load persona config:', error);
            // Fallback to Jane Jacobs defaults if config fails
            createWidget(getDefaultConfig());
        }
    }

    // Fetch persona configuration from API
    async function loadPersonaConfig() {
        const response = await fetch(`${API_URL}/persona/${PERSONA_ID}/config`);
        if (!response.ok) {
            throw new Error(`Failed to load persona config: ${response.status}`);
        }
        const config = await response.json();
        console.log(`✓ Loaded persona: ${config.metadata.name}`);
        return config;
    }

    // Apply persona theme colors as CSS variables
    function applyPersonaTheme(config) {
        if (!config.widget.theme) return;

        const root = document.documentElement;
        const theme = config.widget.theme;

        // Map config keys to CSS variable names
        const colorMap = {
            'primary_color': '--persona-primary-color',
            'cream': '--persona-cream',
            'charcoal': '--persona-charcoal',
            'warm_gray': '--persona-warm-gray',
            'dark_cream': '--persona-dark-cream',
            'text_gray': '--persona-text-gray'
        };

        Object.entries(colorMap).forEach(([configKey, cssVar]) => {
            if (theme[configKey]) {
                root.style.setProperty(cssVar, theme[configKey]);
            }
        });

        // Apply fonts
        if (theme.font_primary) {
            root.style.setProperty('--persona-font-primary', theme.font_primary);
        }
        if (theme.font_secondary) {
            root.style.setProperty('--persona-font-secondary', theme.font_secondary);
        }
    }

    // Get default config (Jane Jacobs fallback)
    function getDefaultConfig() {
        return {
            metadata: { name: 'Jane Jacobs' },
            widget: {
                conversation_starters: [
                    "What do you think about remote work killing downtowns?",
                    "Are 15-minute cities a real idea or just branding?",
                    "What would you say to a city planner today?",
                    "What are cities still getting wrong?"
                ],
                ui: {
                    header_title: 'Jane Jacobs',
                    header_subtitle: '(1916 – )',
                    header_tagline: 'Ask her anything about cities, neighborhoods, or what we keep getting wrong',
                    input_placeholder: 'Ask Jane a question...',
                    error_message: 'Sorry, I encountered an error. Please try again.'
                }
            }
        };
    }

    // Create widget HTML with persona-specific content
    function createWidget(config) {
        const ui = config.widget.ui;
        const starters = config.widget.conversation_starters;

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
                        <h3>${ui.header_title}</h3>
                        <p class="jj-subtitle">${ui.header_subtitle}</p>
                        <p class="jj-tagline">${ui.header_tagline}</p>
                    </div>
                    <button id="jj-close" class="jj-close-btn">&times;</button>
                </div>

                <div id="jj-messages" class="jj-messages">
                    <div class="jj-starters">
                        ${starters.map((starter, i) =>
                            `<button class="jj-starter-btn" data-index="${i}">${starter}</button>`
                        ).join('')}
                    </div>
                </div>

                <div class="jj-input-container">
                    <input
                        type="text"
                        id="jj-input"
                        class="jj-input"
                        placeholder="${ui.input_placeholder}"
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
        attachEventListeners(config);
    }

    // Attach event listeners
    function attachEventListeners(config) {
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
        const starters = config.widget.conversation_starters;
        document.querySelectorAll('.jj-starter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const index = parseInt(btn.getAttribute('data-index'));
                const message = starters[index];
                hideStarters();
                sendMessageWithText(message);
            });
        });
    }

    // Toggle chat window
    function toggleChat() {
        const chatWindow = document.getElementById('jj-chat-window');
        const trigger = document.getElementById('jj-trigger');

        if (isOpen) {
            chatWindow.classList.add('jj-hidden');
            trigger.classList.remove('jj-active');
            isOpen = false;
        } else {
            chatWindow.classList.remove('jj-hidden');
            trigger.classList.add('jj-active');
            isOpen = true;
            enableInput();
        }
    }

    // Close chat window
    function closeChat() {
        const chatWindow = document.getElementById('jj-chat-window');
        const trigger = document.getElementById('jj-trigger');
        chatWindow.classList.add('jj-hidden');
        trigger.classList.remove('jj-active');
        isOpen = false;
    }

    // Enable input after initial open
    function enableInput() {
        const input = document.getElementById('jj-input');
        const sendBtn = document.getElementById('jj-send');
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }

    // Hide conversation starters
    function hideStarters() {
        const starters = document.querySelector('.jj-starters');
        if (starters) {
            starters.style.display = 'none';
        }
    }

    // Send message (from input)
    function sendMessage() {
        const input = document.getElementById('jj-input');
        const message = input.value.trim();

        if (!message || isTyping) return;

        sendMessageWithText(message);
        input.value = '';
    }

    // Send message with specific text
    async function sendMessageWithText(message) {
        hideStarters();
        addMessage('user', message);

        isTyping = true;

        try {
            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            conversationId = data.conversation_id;

            // Add assistant response with typewriter effect
            addMessage('assistant', data.response, true);

        } catch (error) {
            console.error('Error sending message:', error);
            const errorMsg = personaConfig?.widget?.ui?.error_message ||
                           'Sorry, I encountered an error. Please try again.';
            addMessage('assistant', errorMsg);
        } finally {
            isTyping = false;
        }
    }

    // Add message to chat
    function addMessage(role, content, useTypewriter = false) {
        const messagesContainer = document.getElementById('jj-messages');

        const messageDiv = document.createElement('div');
        messageDiv.className = `jj-message jj-message-${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'jj-message-content';

        if (role === 'assistant' && useTypewriter) {
            // Typewriter effect
            typewriterEffect(contentDiv, content);
        } else {
            contentDiv.textContent = content;
        }

        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Typewriter effect with variable speed
    function typewriterEffect(element, text) {
        let i = 0;
        const baseSpeed = 15; // milliseconds per character

        function typeChar() {
            if (i < text.length) {
                const char = text.charAt(i);
                element.textContent += char;

                // Variable speed based on punctuation
                let speed = baseSpeed;
                if (char === '.' || char === '!' || char === '?') {
                    speed = baseSpeed * 15; // Long pause at sentence end
                } else if (char === ',' || char === ';' || char === ':') {
                    speed = baseSpeed * 8; // Medium pause at punctuation
                } else if (char === '\n') {
                    speed = baseSpeed * 10; // Pause at line breaks
                }

                // Add slight randomness for natural feel
                speed *= (0.8 + Math.random() * 0.4);

                i++;

                // Auto-scroll as text appears
                const messagesContainer = document.getElementById('jj-messages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;

                setTimeout(typeChar, speed);
            }
        }

        typeChar();
    }

    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
