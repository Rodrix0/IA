const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');

let isObserving = false;
let screenBreadcrumbs = []; // Mantiene las últimas 5 cosas únicas que miraste
let pollingInterval = null;

// Verifica si la carpeta de scripts existe, y si no, debería estar hecha por el paso anterior
const scriptsDir = path.join(__dirname, '..', 'scripts');
if (!fs.existsSync(scriptsDir)) {
    fs.mkdirSync(scriptsDir, { recursive: true });
}

const psClientPath = path.join(scriptsDir, 'getActiveWindow.ps1');

function toggleObserver(state) {
    if (state === undefined) {
        isObserving = !isObserving;
    } else {
        isObserving = state;
    }

    if (isObserving) {
        if (!pollingInterval) {
            console.log("\n[👁️  Observer] MODO OBSERVADOR ACTIVADO. Jarvis comenzó a mirar las ventanas...");
            pollingInterval = setInterval(pollActiveWindow, 5000); // Lee la pantalla cada 5 segundos
        }
    } else {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            console.log("\n[👀 Observer] MODO OBSERVADOR APAGADO. Privacidad restaurada.");
        }
    }
    return isObserving;
}

function pollActiveWindow() {
    execFile('powershell', ['-ExecutionPolicy', 'Bypass', '-File', psClientPath], (error, stdout) => {
        if (!error && stdout) {
            let activeTitle = stdout.trim();
            // Ignoramos cadenas vacías, la terminal del server o procesos nativos invisibles
            if (activeTitle.length > 2 && 
                !activeTitle.includes("npm") && 
                !activeTitle.includes("powershell") && 
                activeTitle !== "Windows Input Experience" && 
                activeTitle !== "Program Manager") {
                
                let lastAdded = screenBreadcrumbs[screenBreadcrumbs.length - 1];
                
                // Si la ventana cambió y no es la misma que ya estamos mirando
                if (lastAdded !== activeTitle) {
                    screenBreadcrumbs.push(activeTitle);
                    
                    // Solo guardamos un buffer de las últimas 6 actividades
                    if (screenBreadcrumbs.length > 6) {
                        screenBreadcrumbs.shift(); 
                    }
                }
            }
        }
    });
}

function getScreenContext() {
    if (!isObserving || screenBreadcrumbs.length === 0) return null;
    
    // Obtenemos el registro en reverso (de más actual hacia pasado)
    const contextStr = [...screenBreadcrumbs].reverse().join(" | ");
    return `IMPORTANTE: Estoy activamente observando la pantalla del usuario en Windows. Sus ventanas recientes son de más a menos recientes: [ ${contextStr} ]. Usa este contexto si me pregunta sobre 'esto', 'aquello', 'qué estoy viendo' o pide acciones sin darte el objeto explícito.`;
}

module.exports = {
    toggleObserver,
    getScreenContext,
    isObserving: () => isObserving
};
