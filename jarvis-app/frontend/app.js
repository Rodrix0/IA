// --- DOM Elements ---
const ring = document.getElementById('listening-ring');
const userBox = document.getElementById('user-transcript');
const jarvisBox = document.getElementById('jarvis-response');
const btnToggleMic = document.getElementById('btn-toggle-mic');
const modesList = document.getElementById('modes-list');

// Modal Elements
const modeModal = document.getElementById('mode-modal');
const btnOpenModeModal = document.getElementById('btn-open-mode-modal');
const btnCloseModal = document.getElementById('close-modal');
const modeForm = document.getElementById('mode-form');

// --- Socket.io Setup ---
const socket = io(); 

// --- Speech Recognition Setup ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let isSystemActive = false;
let isJarvisSpeaking = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'es-ES'; // Idioma Español

    recognition.onresult = (event) => {
        const current = event.resultIndex;
        const transcript = event.results[current][0].transcript.trim();
        const lowerTranscript = transcript.toLowerCase();
        
        console.log("Reconocido:", transcript);

        // Si el sistema está activo, escuchar
        if (isSystemActive && !isJarvisSpeaking) {
            userBox.textContent = `"${transcript}"`;
            jarvisBox.textContent = "Analizando directiva...";
            setRingState('listening');
            
            // Envía al backend
            socket.emit('process_speech', { text: transcript });
        }
    };

    recognition.onend = () => {
        // Reiniciar automáticamente para escucha pasiva/activa continua si está encendido
        if (isSystemActive) {
            try { recognition.start(); } catch(e){}
        }
    };

    recognition.onerror = (event) => {
        console.error("Speech Recognition Error:", event.error);
        if (event.error === 'not-allowed') {
            jarvisBox.textContent = 'Error: Permisos de micrófono denegados.';
            stopSystem();
        }
    };
} else {
    jarvisBox.textContent = "Error: Tu navegador no soporta reconocimiento de voz (Usa Chrome/Edge).";
}

// --- Text to Speech Setup ---
function speak(text, callback) {
    if (!window.speechSynthesis) {
        console.warn("SpeechSynthesis no soportado");
        return;
    }

    window.speechSynthesis.cancel(); // Cancelar audios previos

    isJarvisSpeaking = true;
    setRingState('speaking');
    jarvisBox.textContent = text;
    userBox.textContent = "..."; 

    // Pausar el reconocimiento mientras Jarvis habla para que no se escuche a sí mismo
    if (recognition && isSystemActive) {
        try { recognition.stop(); } catch(e){}
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES';
    utterance.rate = 1.15; // Un poco más rápido para estilo AI
    utterance.pitch = 1.0;

    // Buscar una voz de Google que suene bien (opcional)
    const voices = window.speechSynthesis.getVoices();
    const googleVoice = voices.find(v => v.name.includes("Google español") || v.lang.includes('es-'));
    if (googleVoice) {
        utterance.voice = googleVoice;
    }

    utterance.onend = () => {
        isJarvisSpeaking = false;
        if(isSystemActive) {
            setRingState('idle');
            try { recognition.start(); } catch(e){}
        }
        if (callback) callback();
    };

    utterance.onerror = (e) => {
        console.error("TTS Error:", e);
        isJarvisSpeaking = false;
        if(isSystemActive) setRingState('idle');
    };

    window.speechSynthesis.speak(utterance);
}

// Ensure voices are loaded (Chrome things)
window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
};

// --- Socket Events Logic ---
socket.on('init_data', (data) => {
    renderModes(data.modes, data.activeModeId);
});

socket.on('modes_updated', (modes) => {
    // Para simplificar, refrescamos la UI consultando la API local, 
    // pero acá nos envian la lista, así que verificamos el activo leyendo clase CSS actual:
    const activeItem = document.querySelector('.mode-list li.active');
    const activeId = activeItem ? activeItem.dataset.id : null;
    renderModes(modes, activeId);
});

socket.on('response', (data) => {
    speak(data.text, () => {
        // Ejecutar acciones visuales una vez termine de hablar
        if (data.action === "OPEN_MODE_MENU") {
            modeModal.classList.remove('hidden');
        } else if (data.action === "MODE_CHANGED") {
            // update UI visually
            document.querySelectorAll('.mode-list li').forEach(li => li.classList.remove('active'));
            const targetLi = document.querySelector(`.mode-list li[data-id="${data.actionPayload}"]`);
            if (targetLi) targetLi.classList.add('active');
        }
    });
});

// --- UI Logic ---
function renderModes(modes, activeId) {
    modesList.innerHTML = '';
    modes.forEach(mode => {
        const li = document.createElement('li');
        li.dataset.id = mode.id;

        // Validar si es el activo
        if (mode.id === activeId) {
            li.classList.add('active');
        }

        li.innerHTML = `
            <strong>${mode.name}</strong>
            <p>${mode.description}</p>
        `;
        
        li.addEventListener('click', () => {
            document.querySelectorAll('.mode-list li').forEach(el => el.classList.remove('active'));
            li.classList.add('active');
            socket.emit('set_mode', mode.id);
            speak(`Modo manual cambiado a ${mode.name}`);
        });

        modesList.appendChild(li);
    });
}

function setRingState(state) {
    ring.className = 'ring'; // reset
    ring.classList.add(state);
}

function startSystem() {
    if (!recognition) return;
    isSystemActive = true;
    btnToggleMic.innerHTML = '<i class="fa-solid fa-power-off"></i> APAGAR SISTEMA';
    btnToggleMic.classList.add('active');
    jarvisBox.textContent = "Sistema en línea. Puedes comenzar a hablar.";
    setRingState('idle');
    try {
        recognition.start();
    } catch(e) {}
    
    speak("Sistema Jarvis en línea a tu disposición.");
}

function stopSystem() {
    isSystemActive = false;
    btnToggleMic.innerHTML = '<i class="fa-solid fa-power-off"></i> INICIAR SISTEMA';
    btnToggleMic.classList.remove('active');
    jarvisBox.textContent = "Sistema fuera de línea.";
    userBox.textContent = "Esperando inicio...";
    setRingState('idle');
    try {
        recognition.stop();
    } catch(e) {}
}

btnToggleMic.addEventListener('click', () => {
    if (isSystemActive) {
        stopSystem();
    } else {
        startSystem();
    }
});

// Modal UI Handlers
btnOpenModeModal.addEventListener('click', () => {
    modeModal.classList.remove('hidden');
});

btnCloseModal.addEventListener('click', () => {
    modeModal.classList.add('hidden');
});

// Form Submission for New Mode
modeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('mode-name').value;
    const description = document.getElementById('mode-desc').value;

    try {
        const response = await fetch('/api/modes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        if (response.ok) {
            modeModal.classList.add('hidden');
            modeForm.reset();
            speak(`He registrado el nuevo estrato cerebral bajo el nombre: ${name}.`);
        }
    } catch (err) {
        console.error("Error creating mode:", err);
        jarvisBox.textContent = "Error al conectar con la base de datos de modos.";
    }
});
