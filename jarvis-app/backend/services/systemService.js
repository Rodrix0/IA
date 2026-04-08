const { exec } = require('child_process');
const os = require('os');
const fs = require('fs');
const path = require('path');

// --- 1. Scraper Dinámico ---
async function buscarEnYoutube(query) {
    const queryFormateado = encodeURIComponent(query);
    const urlBusqueda = `https://www.youtube.com/results?search_query=${queryFormateado}`;
    
    try {
        const respuesta = await fetch(urlBusqueda);
        // Simplemente devolvemos la URL de búsqueda en vez de forzar a abrir el primer video
        return urlBusqueda;
    } catch (error) {
        console.error("Falló la búsqueda:", error);
    }
    return "https://www.youtube.com"; // Fallback general
}

// --- 2. Sistema de Memoria Persistente ---
async function procesarMemoriaDinamica(busqueda) {
    const archivoMemoria = path.join(__dirname, '..', 'data', 'memoria.json');
    let memoria = {};

    // Nos aseguramos de que el sistema de memoria exista
    if (!fs.existsSync(path.dirname(archivoMemoria))) {
        fs.mkdirSync(path.dirname(archivoMemoria), { recursive: true });
    }

    // Leemos la memoria si el archivo ya existe
    if (fs.existsSync(archivoMemoria)) {
        try {
            memoria = JSON.parse(fs.readFileSync(archivoMemoria, 'utf8'));
        } catch (e) {
            console.error("Error leyendo memoria.json:", e);
        }
    }

    // Revisamos si ya conocemos la búsqueda (si existe en el cerebro)
    if (memoria[busqueda]) {
        console.log(`[Memoria Local]: Recordando link para "${busqueda}". Abriendo...`);
        return memoria[busqueda];
    } else {
        console.log(`[Búsqueda Dinámica]: Navegando en internet para aprender "${busqueda}"...`);
        
        // Scraper actual enfocado en YouTube, en el futuro se pueden añadir otros
        const nuevoLink = await buscarEnYoutube(busqueda);
        
        // Lo guardamos en el JSON para no tener que buscarlo nunca más
        memoria[busqueda] = nuevoLink;
        fs.writeFileSync(archivoMemoria, JSON.stringify(memoria, null, 2));
        
        return nuevoLink;
    }
}

// --- 3. Ejecutor Central ---
async function openApp(appName) {
    const platform = os.platform();
    let command = '';
    const lowerApp = appName.toLowerCase();

    // Mapeo básico estricto (solo palabras puras)
    const pcGamesMap = {
        'steam': 'start steam://',
        'epic games': 'start com.epicgames.launcher://',
        'league of legends': 'start "" "C:\\Riot Games\\Riot Client\\RiotClientServices.exe" --launch-product=league_of_legends --launch-patchline=live',
        'minecraft': 'start minecraft://'
    };

    // A. ¿Es un juego/programa de la PC exacto?
    for (const [key, cmd] of Object.entries(pcGamesMap)) {
        if (lowerApp === key || lowerApp === `el ${key}`) {
            command = platform === 'win32' ? cmd : `open "${key}"`;
            break;
        }
    }

    // B. ¿Es una aplicación nativa tradicional?
    if (!command) {
        if (lowerApp === 'calculadora' || lowerApp === 'calc') {
            command = platform === 'win32' ? 'calc' : 'open -a Calculator';
        } else if (lowerApp === 'chrome' || lowerApp === 'google chrome') {
            command = platform === 'win32' ? 'start chrome' : 'open -a "Google Chrome"';
        // Casos web crudos pero directos
        } else if (lowerApp === 'youtube') {
            command = platform === 'win32' ? `start https://youtube.com` : `open https://youtube.com`;
        } else if (lowerApp === 'netflix') {
            command = platform === 'win32' ? `start https://netflix.com` : `open https://netflix.com`;
        } else if (lowerApp === 'spotify') {
            command = platform === 'win32' ? `start https://open.spotify.com` : `open https://open.spotify.com`;
        }
    }

    // C. El núcleo de tu idea: Si es una frase desconocida ("el canal de goncho", "tutorial de java")
    // Lo enviamos al sistema dinámico de memoria
    if (!command) {
        const urlObtenida = await procesarMemoriaDinamica(lowerApp);
        command = platform === 'win32' ? `start ${urlObtenida}` : platform === 'darwin' ? `open "${urlObtenida}"` : `xdg-open "${urlObtenida}"`;
    }

    // Ejecutar orden en el Sistema Operativo
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
