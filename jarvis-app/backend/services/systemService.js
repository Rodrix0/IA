const { exec } = require('child_process');
const os = require('os');

function openApp(appName) {
    const platform = os.platform();
    let command = '';

    const lowerApp = appName.toLowerCase();

    if (platform === 'win32') {
        if (lowerApp.includes('chrome')) {
            command = 'start chrome';
        } else if (lowerApp.includes('calculadora') || lowerApp.includes('calc')) {
            command = 'calc';
        } else if (lowerApp.includes('vs code') || lowerApp.includes('code') || lowerApp.includes('visual studio')) {
            command = 'code';
        } else {
            // General fallback para Windows
            command = `start ${appName}`;
        }
    } else if (platform === 'darwin') {
        if (lowerApp.includes('chrome')) {
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
        command = `${appName} &`;
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
    const lowerText = text.toLowerCase();
    // Revisa si el comando empieza con "abrir"
    if (lowerText.startsWith("abrir ")) {
        // Extrae el resto del texto
        const appToOpen = text.substring(6).trim();
        return { isSystemCommand: true, appName: appToOpen };
    }
    return { isSystemCommand: false };
}

module.exports = {
    openApp,
    handleSystemCommand
};
