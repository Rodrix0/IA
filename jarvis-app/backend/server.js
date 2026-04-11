const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const modeService = require('./services/modeService');
const systemService = require('./services/systemService');
const aiService = require('./services/aiService');
const backgroundTuner = require('./services/backgroundTuner');
const observerService = require('./services/observerService');
const appDiscoveryService = require('./services/appDiscoveryService');
const hotkeyService = require('./services/hotkeyService');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: { origin: '*' }
});

app.use(cors());
app.use(express.json());

// Servir frontend si se corre el server directo (opcional para facilidad)
app.use(express.static(path.join(__dirname, '../frontend')));

// API Rest para Modos (usado por el cliente cuando quiere crear nuevos modos usando la interfaz)
app.get('/api/modes', (req, res) => {
    res.json(modeService.getAllModes());
});

app.post('/api/modes', (req, res) => {
    const { name, description } = req.body;
    if (!name || !description) {
        return res.status(400).json({ error: "El nombre y descripción son requeridos." });
    }
    const newMode = modeService.addMode({ name, description });
    // Al notificar a todos los clientes actualizamos su lista
    io.emit('modes_updated', modeService.getAllModes());
    res.json(newMode);
});

// Real-time voice processing y Eventos del Socket
io.on('connection', (socket) => {
    console.log('[+] Interfaz conectada a Jarvis (Socket ID: ' + socket.id + ')');

    // Inicializar data en frontend
    socket.emit('init_data', {
        modes: modeService.getAllModes(),
        activeModeId: modeService.getActiveMode().id
    });

    // Evento de procesamiento de voz (cuando Jarvis escucha al usuario)
    socket.on('process_speech', async (data) => {
        const text = data.text;
        const lowerText = text.toLowerCase();
        console.log(`[Usuario dice]: ${text}`);

        let responseText = "";
        let action = null;
        let actionPayload = null;

        try {
            // 0. Toggle de Observador/Estudio Activo
            const turnOnWords = ['activar observador', 'activa observador', 'activa el observador', 'modo observador', 'modo observación', 'modo observacion', 'estudio activo', 'inicia observador', 'enciende el observador'];
            const turnOffWords = ['desactivar observador', 'desactiva observador', 'apaga observador', 'apaga el observador', 'apaga observacion', 'apaga observación', 'desactiva estudio activo'];

            if (turnOnWords.some(w => lowerText.includes(w))) {
                observerService.toggleObserver(true);
                responseText = "Modo Estudio Activo habilitado. He activado mi red de escaneo neuromotriz; a partir de ahora analizaré tus ventanas para brindarte ayuda contextual.";
                action = "OBSERVER_ON";
            } 
            else if (turnOffWords.some(w => lowerText.includes(w))) {
                observerService.toggleObserver(false);
                responseText = "Modo Estudio Activo deshabilitado. Mis ojos locales sobre el sistema operativo han sido apagados.";
                action = "OBSERVER_OFF";
            }
            // 1. Detección de comandos específicos
            else if (lowerText.includes('abrir menú de carga de modos') || lowerText.includes('crear modo') || lowerText.includes('nuevo modo')) {
                responseText = "Abriendo el panel de creación de modalidades.";
                action = "OPEN_MODE_MENU";
            } 
            else if (lowerText.includes('mostrar modos')) {
                responseText = "Mostrando los modos disponibles de mi sistema.";
                action = "SHOW_MODES";
            }
            else if (lowerText.includes('activar modo')) {
                const modeNameMatch = lowerText.replace('activar modo', '').replace('el', '').trim();
                const modes = modeService.getAllModes();
                
                // Encontrar el modo que coincida
                const targetMode = modes.find(m => m.name.toLowerCase() === modeNameMatch || m.id === modeNameMatch);
                
                if (targetMode) {
                    modeService.setActiveMode(targetMode.id);
                    responseText = `He cambiado mi configuración cerebral al modo ${targetMode.name}.`;
                    action = "MODE_CHANGED";
                    actionPayload = targetMode.id;
                    io.emit('modes_updated', modeService.getAllModes());
                } else {
                    responseText = `No pude encontrar en mi base de datos un modo llamado ${modeNameMatch}.`;
                }
            }
            else {
                // 2. Comandos de sistema (Abrir apps y Entrenamientos) - Conservamos la Vía Rápida primero
                const sysCommand = systemService.handleSystemCommand(text);
                
                if (sysCommand.isTraining) {
                    systemService.saveCustomCommand(sysCommand.trigger, sysCommand.appName);
                    responseText = `Entendido. A partir de ahora, cuando me digas "${sysCommand.trigger}", abriré ${sysCommand.appName}.`;
                    action = "TRAINING_SAVED";
                }
                else if (sysCommand.isSystemCommand && sysCommand.isLearned) {
                    // Solo interceptamos en la capa rápida si es un comando EXPLÍCITAMENTE aprendido o muy simple
                    responseText = `Comando aprendido detectado. Ejecutando ${sysCommand.appName}, señor.`;
                        
                    const activeMode = modeService.getActiveMode();
                    const success = await systemService.openApp(sysCommand.appName, activeMode.id);
                    if (!success) {
                        responseText = `Hubo un inconveniente al intentar abrir la aplicación ${sysCommand.appName}.`;
                    }
                }
                // 3. Respuesta de IA (Cerebro Híbrido) - Delega todo lo demás a Ollama
                else {
                    const activeMode = modeService.getActiveMode();
                    const screenContext = observerService.getScreenContext();
                    responseText = await aiService.getAIResponse(text, activeMode, screenContext);
                }
            }

        } catch (error) {
            console.error(error);
            responseText = "Lo siento, mi sistema interceptó una excepción no controlada.";
        }

        console.log(`[Jarvis Responde]: ${responseText}`);
        socket.emit('response', { text: responseText, action, actionPayload });
    });

    // Evento manual para cambiar de modo desde la UI
    socket.on('set_mode', (modeId) => {
        if(modeService.setActiveMode(modeId)) {
            io.emit('modes_updated', modeService.getAllModes());
        }
    });

    socket.on('disconnect', () => {
        console.log('[-] Interfaz desconectada (' + socket.id + ')');
    });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`\n===========================================`);
    console.log(`  JARVIS VIRTUAL ASSISTANT - BACKEND ACTIVE`);
    console.log(`  => Server running on http://localhost:${PORT}`);
    console.log(`===========================================\n`);
    
    // Iniciar el estudio automático en segundo plano
    backgroundTuner.startBackgroundStudying();
    // Iniciar el indexador de accesos directos
    appDiscoveryService.triggerBackgroundScan();
    // Conectar el gancho USB/Teclado físico
    hotkeyService.initHotkeyService(io);
});
