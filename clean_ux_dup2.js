const fs = require('fs');
const file = 'c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/app.js';
let code = fs.readFileSync(file, 'utf8');

const sIdx = code.indexOf('const btnCopy = document.getElementById(\\\'btn-copy-doc\\\');');
if (sIdx !== -1) {
    code = code.substring(0, sIdx);
    
    // Add the clean version once
    code += \
const btnCopy = document.getElementById('btn-copy-doc');
const btnStop = document.getElementById('btn-stop-audio');

if (btnCopy) {
    btnCopy.addEventListener('click', () => {
        const textToCopy = document.getElementById('jarvis-response').innerText; 
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
        isJarvisSpeaking = false;
        if(typeof setRingState !== 'undefined') { setRingState('idle'); }
        btnStop.innerHTML = '<i class="fa-solid fa-check"></i> Silenciado';
        setTimeout(() => btnStop.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> Detener Audio', 2500);
    });
}

function hideUXButtons() {
    const b1 = document.getElementById('btn-copy-doc');
    const b2 = document.getElementById('btn-stop-audio');
    if(b1) b1.style.display = 'none';
    if(b2) b2.style.display = 'none';
}
\;

    fs.writeFileSync(file, code, 'utf8');
}
