const fs = require('fs');
const file = 'c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/app.js';
let code = fs.readFileSync(file, 'utf8');

const base = code.replace(/const btnCopy = document.getElementById\('btn-copy-doc'\);/g, '')
                 .replace(/const btnStop = document.getElementById\('btn-stop-audio'\);/g, '')
                 .replace(/function hideUXButtons\(\) \{.*?\}/gs, '');

const finalApp = base + \\n
document.addEventListener('DOMContentLoaded', () => {
    const btnCopy = document.getElementById('btn-copy-doc');
    const btnStop = document.getElementById('btn-stop-audio');

    if (btnCopy) {
        btnCopy.addEventListener('click', () => {
            const textToCopy = jarvisBox.innerText; 
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalIcon = btnCopy.innerHTML;
                btnCopy.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
                setTimeout(() => btnCopy.innerHTML = originalIcon, 2500);
            });
        });
    }

    if (btnStop) {
        btnStop.addEventListener('click', () => {
            window.speechSynthesis.cancel();
            if(window.isJarvisSpeaking !== undefined) isJarvisSpeaking = false;
            setRingState('idle');
            btnStop.innerHTML = '<i class="fa-solid fa-check"></i> Silenciado';
            setTimeout(() => btnStop.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> Detener Audio', 2500);
        });
    }
});

function hideUXButtons() {
    const b1 = document.getElementById('btn-copy-doc');
    const b2 = document.getElementById('btn-stop-audio');
    if(b1) b1.style.display = 'none';
    if(b2) b2.style.display = 'none';
}
\;

fs.writeFileSync(file, finalApp, 'utf8');
