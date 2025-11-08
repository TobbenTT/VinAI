// Espera a que todo el HTML esté cargado antes de ejecutar el script
document.addEventListener('DOMContentLoaded', () => {

    // --- Selección de Elementos del DOM (Chatbot) ---
    const chatContainer = document.getElementById('chat-container');
    const chatBubble = document.getElementById('chat-bubble');
    const closeButton = document.getElementById('close-button');
    const messagesDiv = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-button');
    const speakerButton = document.getElementById('speaker-button');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // === NOVEDAD: Selector para los botones fijos ===
    const quickRepliesDiv = document.getElementById('quick-replies');
    // === FIN NOVEDAD ===

    // --- Configuración y Constantes ---
    const RASA_API_URL = 'http://localhost:5005/webhooks/rest/webhook';
    const BOT_NAME = 'VinAI Sommelier'; 

    let RASA_SENDER_ID = localStorage.getItem('vinai_user_id') || `session_${Date.now()}`;

    // --- (Funciones: createAvatarUrl, Avatares, Variables de Estado, toggleChat) ---
    // ... (Tu código para estas funciones va aquí, no cambia) ...
    function createAvatarUrl(text, backgroundColor, textColor) {
        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" width="35" height="35">
                <circle cx="17.5" cy="17.5" r="17.5" fill="${backgroundColor}" />
                <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="${textColor}" font-size="16" font-family="Montserrat, sans-serif" font-weight="600">${text}</text>
            </svg>
        `;
        return `data:image/svg+xml;base64,${btoa(svg)}`;
    }
    const BOT_AVATAR_URL = createAvatarUrl('AI', '#1A1A1A', '#D4AF37'); 
    const USER_AVATAR_URL = createAvatarUrl('TÚ', '#D4AF37', '#1A1A1A'); 
    let recognition; 
    let isListening = false;
    let isSpeakingEnabled = true; 
    function toggleChat() {
        chatContainer.classList.toggle('open');
        if (chatContainer.classList.contains('open') && messagesDiv.children.length === 0) {
            sendPayload('/saludar', ''); 
            userInput.focus();
        }
    }
    // --- Fin de funciones ---

    function addMessage(sender, text, customData = {}) {
        if (sender === 'user' && !text.trim()) {
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        const avatar = document.createElement('img');
        avatar.classList.add('avatar');
        avatar.src = sender === 'bot' ? BOT_AVATAR_URL : USER_AVATAR_URL;
        avatar.alt = sender === 'bot' ? BOT_NAME : 'Tú';

        const bubble = document.createElement('div');
        bubble.classList.add('bubble');
        
        const textElement = document.createElement('div');
        textElement.innerHTML = text; 
        bubble.appendChild(textElement);

        if (customData.image) {
            const imageElement = document.createElement('img');
            imageElement.src = customData.image;
            imageElement.classList.add('chat-image');
            bubble.appendChild(imageElement);
        }

        if (customData.link) {
            const linkElement = document.createElement('a');
            linkElement.href = customData.link;
            linkElement.target = '_blank';
            linkElement.textContent = customData.link_text || 'Ver Detalle';
            bubble.appendChild(linkElement);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(bubble);
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight; 
    }

    function showTypingIndicator(show) {
        typingIndicator.style.display = show ? 'flex' : 'none';
        if (show) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }
    
    // === NOVEDAD: Función para manejar los botones ===
    function handleBotButtons(buttons) {
        // Limpiamos botones dinámicos anteriores
        const existingButtons = document.getElementById('dynamic-quick-replies');
        if (existingButtons) {
            existingButtons.remove();
        }

        if (!buttons || buttons.length === 0) {
            // Si no hay botones nuevos, mostramos los fijos
            quickRepliesDiv.style.display = 'flex';
            return;
        }

        // Si hay botones nuevos, ocultamos los fijos
        quickRepliesDiv.style.display = 'none';

        // Creamos el nuevo contenedor de botones
        const dynamicRepliesDiv = document.createElement('div');
        dynamicRepliesDiv.id = 'dynamic-quick-replies';
        dynamicRepliesDiv.className = 'quick-replies-container'; // Usaremos el mismo estilo
        
        buttons.forEach(button => {
            const buttonElement = document.createElement('button');
            buttonElement.textContent = button.title;
            buttonElement.addEventListener('click', () => {
                // Enviamos el payload del botón
                sendPayload(button.payload, button.title);
                // Removemos los botones dinámicos
                dynamicRepliesDiv.remove();
                // Mostramos los botones fijos de nuevo
                quickRepliesDiv.style.display = 'flex';
            });
            dynamicRepliesDiv.appendChild(buttonElement);
        });

        // Añadimos el nuevo div de botones justo encima del área de input
        userInput.parentElement.insertAdjacentElement('beforebegin', dynamicRepliesDiv);
    }
    // === FIN DE NOVEDAD ===


    async function sendMessageToRasa(message) {
        if (!message.trim()) return; 

        addMessage('user', message);
        userInput.value = ''; 
        showTypingIndicator(true); 
        
        // === NOVEDAD: Ocultamos los botones fijos al enviar mensaje ===
        handleBotButtons(null); // Esto los oculta temporalmente
        // === FIN NOVEDAD ===

        try {
            const response = await fetch(RASA_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sender: RASA_SENDER_ID, message: message })
            });

            const data = await response.json();
            showTypingIndicator(false); 

            if (data && data.length > 0) {
                // === NOVEDAD: Reiniciamos la bandera de botones ===
                let hasButtons = false;
                
                for (const botMessage of data) {
                    const messageText = botMessage.text || '';
                    const custom = botMessage.custom || {};
                    
                    if (custom.user_id) {
                        RASA_SENDER_ID = custom.user_id;
                        localStorage.setItem('vinai_user_id', RASA_SENDER_ID);
                        console.log(`Usuario logueado. Sender ID es ahora: ${RASA_SENDER_ID}`);
                    }
                    
                    addMessage('bot', messageText, { 
                        link: custom.link, 
                        link_text: custom.link_text,
                        image: botMessage.image
                    });
                    
                    if (isSpeakingEnabled && messageText) {
                        speakText(messageText);
                    }
                    
                    // === NOVEDAD: Capturamos los botones ===
                    if (botMessage.buttons && botMessage.buttons.length > 0) {
                        handleBotButtons(botMessage.buttons);
                        hasButtons = true;
                    }
                }
                
                // Si ningún mensaje tuvo botones, mostramos los fijos
                if (!hasButtons) {
                    quickRepliesDiv.style.display = 'flex';
                }
            } else {
                addMessage('bot', 'Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?');
                quickRepliesDiv.style.display = 'flex'; // Mostrar fijos en caso de error
            }
        } catch (error) {
            console.error('Error al comunicarse con Rasa:', error);
            showTypingIndicator(false);
            addMessage('bot', 'Hubo un error al conectar con el asistente. Por favor, inténtalo de nuevo más tarde.');
            quickRepliesDiv.style.display = 'flex'; // Mostrar fijos en caso de error
        }
    }
    
    async function sendPayload(payload, title) {
        if (title) {
            addMessage('user', title); 
        }
        showTypingIndicator(true);
        
        // === NOVEDAD: Ocultamos los botones fijos al enviar payload ===
        handleBotButtons(null); // Esto los oculta temporalmente
        // === FIN NOVEDAD ===
        
        try {
            const response = await fetch(RASA_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sender: RASA_SENDER_ID, message: payload })
            });
            const data = await response.json();
            showTypingIndicator(false);

            if (data && data.length > 0) {
                // === NOVEDAD: Reiniciamos la bandera de botones ===
                let hasButtons = false;

                for (const botMessage of data) {
                    const messageText = botMessage.text || '';
                    const custom = botMessage.custom || {};

                     if (custom.user_id) {
                        RASA_SENDER_ID = custom.user_id;
                        localStorage.setItem('vinai_user_id', RASA_SENDER_ID);
                        console.log(`Usuario logueado. Sender ID es ahora: ${RASA_SENDER_ID}`);
                    }
                    
                    addMessage('bot', messageText, { 
                        link: custom.link, 
                        link_text: custom.link_text,
                        image: botMessage.image
                    });
                    
                    if (isSpeakingEnabled && messageText) {
                        speakText(messageText);
                    }
                    
                    // === NOVEDAD: Capturamos los botones ===
                    if (botMessage.buttons && botMessage.buttons.length > 0) {
                        handleBotButtons(botMessage.buttons);
                        hasButtons = true;
                    }
                }
                
                // Si ningún mensaje tuvo botones, mostramos los fijos
                if (!hasButtons) {
                    quickRepliesDiv.style.display = 'flex';
                }
            }
        } catch (error) {
            console.error('Error al enviar payload a Rasa:', error);
            showTypingIndicator(false);
            addMessage('bot', 'Hubo un error al procesar tu selección. Por favor, inténtalo de nuevo.');
            quickRepliesDiv.style.display = 'flex'; // Mostrar fijos en caso de error
        }
    }

    // --- (Funciones: initSpeechRecognition, speakText) ---
    // ... (Tu código para estas funciones va aquí, no cambia) ...
    function initSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window)) {
            voiceButton.style.display = 'none'; 
            return;
        }
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false; 
        recognition.lang = 'es-ES'; 
        recognition.interimResults = false; 
        recognition.onstart = () => { isListening = true; voiceButton.classList.add('active'); };
        recognition.onresult = (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript;
            userInput.value = transcript; 
            sendMessageToRasa(transcript); 
        };
        recognition.onerror = (event) => { console.error("Error de voz:", event.error); isListening = false; voiceButton.classList.remove('active'); };
        recognition.onend = () => { isListening = false; voiceButton.classList.remove('active'); };
    }
    function speakText(text) {
        if (!isSpeakingEnabled || !('speechSynthesis' in window)) return;
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-ES'; 
        utterance.rate = 1.2; 
        speechSynthesis.speak(utterance);
    }
    // --- Fin de funciones ---

    // --- Inicialización y Asignación de Eventos (Chatbot) ---
    initSpeechRecognition(); 
    chatBubble.addEventListener('click', toggleChat); 
    closeButton.addEventListener('click', toggleChat); 
    sendButton.addEventListener('click', () => sendMessageToRasa(userInput.value)); 
    userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessageToRasa(userInput.value); }); 
    voiceButton.addEventListener('click', () => { 
        if (!recognition) return;
        if (isListening) { recognition.stop(); } 
        else { try { recognition.start(); } catch(e) { console.error("Error al iniciar escucha:", e); } }
    });
    speakerButton.addEventListener('click', () => { 
        isSpeakingEnabled = !isSpeakingEnabled;
        speakerButton.innerHTML = isSpeakingEnabled ? '<i class="fas fa-volume-up"></i>' : '<i class="fas fa-volume-mute"></i>';
        if (!isSpeakingEnabled) speechSynthesis.cancel(); 
    });
    
    // === NOVEDAD: Modificado para usar la variable quickRepliesDiv ===
    quickRepliesDiv.querySelectorAll('button').forEach(button => { 
        button.addEventListener('click', () => {
            sendPayload(button.dataset.payload, button.textContent);
        });
    });
    // === FIN NOVEDAD ===
    
    // ------------------------------------------------------------------
    // --- LÓGICA DEL MODAL DE LOGIN/REGISTRO DE USUARIO ---
    // --- (Esta parte no necesita cambios) ---
    // ------------------------------------------------------------------

    // --- Selectores del Modal ---
    const userModalBackdrop = document.getElementById('user-modal-backdrop');
    const userModal = document.getElementById('user-modal');
    const modalCloseButton = document.getElementById('modal-close-button');
    const userNavLink = document.querySelector('.nav-link[href="http://localhost:8080/login"]'); 
    const profileLink = document.createElement('a');
    profileLink.href = 'http://localhost:8080/profile'; 
    profileLink.target = '_blank';
    profileLink.textContent = 'Mi Perfil';
    profileLink.className = 'nav-link';
    profileLink.style.color = '#D4AF37';
    profileLink.style.fontWeight = '700';
    profileLink.style.display = 'none'; 
    if (userNavLink) {
        userNavLink.parentElement.insertAdjacentElement('beforebegin', profileLink);
    }
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const showRegisterLink = document.getElementById('show-register-link');
    const showLoginLink = document.getElementById('show-login-link');
    const modalTitle = document.getElementById('modal-title');
    const loginError = document.getElementById('login-error');
    const registerError = document.getElementById('register-error');

    // --- Funciones del Modal ---
    function openModal() { userModalBackdrop.style.display = 'block'; userModal.style.display = 'block'; }
    function closeModal() { userModalBackmDrop.style.display = 'none'; userModal.style.display = 'none'; loginError.textContent = ''; registerError.textContent = ''; }
    function showRegisterForm() { loginForm.style.display = 'none'; registerForm.style.display = 'block'; showRegisterLink.style.display = 'none'; showLoginLink.style.display = 'block'; modalTitle.textContent = 'Crear Cuenta'; }
    function showLoginForm() { loginForm.style.display = 'block'; registerForm.style.display = 'none'; showRegisterLink.style.display = 'block'; showLoginLink.style.display = 'none'; modalTitle.textContent = 'Iniciar Sesión'; }

    // --- Asignación de Eventos del Modal ---
    if (userNavLink) {
        userNavLink.href = "javascript:void(0);"; 
        userNavLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (localStorage.getItem('vinai_user_id')) {
                if (confirm('¿Estás seguro de que quieres cerrar sesión?')) {
                    fetch('http://localhost:8080/public_logout', { credentials: 'include' })
                        .then(() => {
                            localStorage.removeItem('vinai_user_id');
                            location.reload(); 
                        });
                }
            } else {
                openModal();
                showLoginForm();
            }
        });
    }
    modalCloseButton.addEventListener('click', closeModal);
    userModalBackdrop.addEventListener('click', closeModal);
    showRegisterLink.addEventListener('click', showRegisterForm);
    showLoginLink.addEventListener('click', showLoginForm);

    // --- Evento Formulario Login ---
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.textContent = '';
        const email = loginForm.email.value;
        const password = loginForm.password.value;
        try {
            const response = await fetch('http://localhost:8080/public_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
                credentials: 'include' 
            });
            const data = await response.json();
            if (data.success) {
                RASA_SENDER_ID = data.user_id;
                localStorage.setItem('vinai_user_id', data.user_id); 
                profileLink.style.display = 'inline-block'; 
                userNavLink.textContent = 'Cerrar Sesión'; 
                closeModal();
                sendPayload('/saludar', ''); 
            } else {
                loginError.textContent = data.message;
            }
        } catch (err) {
            loginError.textContent = 'Error de conexión con el servidor.';
        }
    });

    // --- Evento Formulario Registro ---
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        registerError.textContent = '';
        const username = registerForm.username.value;
        const email = registerForm.email.value;
        const password = registerForm.password.value;
        try {
            const response = await fetch('http://localhost:8080/public_register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password }),
                credentials: 'include'
            });
            const data = await response.json();
            if (data.success) {
                showLoginForm();
                loginError.textContent = data.message; 
            } else {
                registerError.textContent = data.message;
            }
        } catch (err) {
            registerError.textContent = 'Error de conexión con el servidor.';
        }
    });

    // --- Lógica al Cargar la Página (Verificación de Sesión) ---
    (async function checkUserSession() {
        try {
            const response = await fetch('http://localhost:8080/check_session', {
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error('El servidor de sesión no responde.');
            }
            const data = await response.json();
            if (data.logged_in) {
                profileLink.style.display = 'inline-block'; 
                userNavLink.textContent = 'Cerrar Sesión';
                localStorage.setItem('vinai_user_id', data.user_id);
                RASA_SENDER_ID = data.user_id;
            } else {
                profileLink.style.display = 'none';
                userNavLink.textContent = 'Usuario';
                localStorage.removeItem('vinai_user_id');
            }
        } catch (err) {
            console.error("Error al verificar la sesión:", err);
            profileLink.style.display = 'none';
            userNavLink.textContent = 'Usuario';
            localStorage.removeItem('vinai_user_id');
        }
    })(); 

}); // Cierre del 'DOMContentLoaded'