const { exec } = require('child_process');
const os = require('os');

function openApp(appName) {
    const platform = os.platform();
    let command = '';

    const lowerApp = appName.toLowerCase();

    // Mapeo automático de páginas web populares (Jarvis abrirá tu navegador por defecto)
    const websiteMap = {
        'youtube': 'https://www.youtube.com',
        'google': 'https://www.google.com',
        'netflix': 'https://www.netflix.com',
        'spotify': 'https://open.spotify.com',
        'facebook': 'https://www.facebook.com',
        'instagram': 'https://www.instagram.com',
        'whatsapp': 'https://web.whatsapp.com',
        'chat gpt': 'https://chat.openai.com',
        'chatgpt': 'https://chat.openai.com',
        'twitter': 'https://twitter.com'
    };

    // Mapeo de juegos o software complejo. 
    // Si tu juego requiere una ruta exacta (ej. "C:\\Juegos\\MiJuego.exe"), ponla aquí.
    const pcGamesMap = {
        'steam': 'start steam://',
        'epic games': 'start com.epicgames.launcher://',
        'league of legends': 'start "" "C:\\Riot Games\\Riot Client\\RiotClientServices.exe" --launch-product=league_of_legends --launch-patchline=live',
        'minecraft': 'start minecraft://'
    };

    let targetUrl = null;
    let customWinCmd = null;

    // Buscar si es un sitio web
    for (const [key, url] of Object.entries(websiteMap)) {
        if (lowerApp.includes(key)) {
            targetUrl = url;
            break;
        }
    }

    // Buscar si es un juego de PC con ruta configurada
    if (!targetUrl) {
        for (const [key, cmd] of Object.entries(pcGamesMap)) {
            if (lowerApp.includes(key)) {
                customWinCmd = cmd;
                break;
            }
        }
    }

    if (platform === 'win32') {
        if (customWinCmd) {
            command = customWinCmd;
        } else if (targetUrl) {
            command = `start ${targetUrl}`; // Abre la URL web
        } else if (lowerApp.includes('chrome')) {
            command = 'start chrome';
        } else if (lowerApp.includes('calculadora') || lowerApp.includes('calc')) {
            command = 'calc';
        } else if (lowerApp.includes('vs code') || lowerApp.includes('code') || lowerApp.includes('visual studio')) {
            command = 'code';
        } else {
            // General fallback: Intenta iniciar el ejecutable por su nombre
            command = `start ${appName}`;
        }
    } else if (platform === 'darwin') {
        if (targetUrl) {
            command = `open ${targetUrl}`;
        } else if (lowerApp.includes('chrome')) {
            command = 'open -a "Google Chrome"';
        } else if (lowerApp.includes('calculadora')) {
            command = 'open -a Calculator';
        } else if (lowerApp.includes('vs code') || lowerApp.includes('code')) {
            command = 'open -a "Visual Studio Code"';
        } else {
            command = `open -a "${appName}"`;
        }
    } else {
        // Fallback para Linux
        if (targetUrl) {
            command = `xdg-open ${targetUrl}`;
        } else {
            command = `${appName} &`;
        }
    }

    return new Promise((resolve) => {
        exec(command, (error) => {
            if (error) {
                console.error(`Error al abrir app: ${error.message}`);
                resolve(false);
            } else {
                resolve(true);
            }
        });
    });
}

function handleSystemCommand(text) {
    let lowerText = text.toLowerCase();

    // Usar expresión regular para encontrar "abre [algo]" o "abrir [algo]"
    // sin importar si el usuario dice "Jarvis abre X" o "por favor abre Y".
    const match = lowerText.match(/(?:abre|abrir) (.+)/i);

    if (match) {
        let appToOpen = match[1].trim();
        // Limpiar puntos finales típicos del reconocimiento de voz
        if (appToOpen.endsWith('.')) {
            appToOpen = appToOpen.slice(0, -1);
        }
        return { isSystemCommand: true, appName: appToOpen };
    }

    return { isSystemCommand: false };
}

module.exports = {
    openApp,
    handleSystemCommand
};
