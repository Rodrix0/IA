const cheerio = require('cheerio');

// Eliminamos las credenciales de Google porque ahora somos 100% locales
let conversationHistory = [];

async function performInvisibleSearch(query) {
    console.log(`\n[Agente Araña] 🕸️ Infiltrando motor de búsqueda secundario (Yahoo) para: "${query}"...`);
    try {
        const response = await fetch(`https://es.search.yahoo.com/search?p=${encodeURIComponent(query)}`, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        });
        
        const html = await response.text();
        const $ = cheerio.load(html);
        
        // Arrancamos estilos y scripts para dejar solo texto legible
        $('script, style, noscript, header, footer, svg, img, button').remove();
        
        // Extraemos el texto de Yahoo (Los cuadros mágicos de Yahoo se renderizan sin bloqueos de Cookies)
        let scrapedText = $('#main').text() || $('body').text();
        scrapedText = scrapedText.replace(/\s+/g, ' ').trim();
        
        // Le pasamos los primeros 2500 caracteres a Llama 3
        scrapedText = scrapedText.substring(0, 2500);
        
        if (!scrapedText.trim()) {
            return "El túnel de búsqueda está bloqueado, no se obtuvieron resultados.";
        }
        return scrapedText;
    } catch (e) {
        console.error("Error al romper la seguridad de búsqueda:", e.message);
        return "Fallo de conexión al raspar la web.";
    }
}

async function fetchOllamaResponse(prompt) {
    const response = await fetch('http://127.0.0.1:11434/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'llama3', 
            prompt: prompt,
            stream: false,
            format: 'json' // Obligamos a Ollama a responder en formato JSON!
        })
    });

    if (!response.ok) {
        throw new Error(`Ollama devolvió un error HTTP: ${response.status}`);
    }

    const data = await response.json();
    try {
        return JSON.parse(data.response); // Parseamos el JSON que nos dio Ollama
    } catch (e) {
        console.error("Error parseando respuesta JSON de Ollama:", data.response);
        return { action: "chat", reply: "Hubo un error interpretando mi cerebro neuronal." };
    }
}

async function getAIResponse(userText, activeMode, screenContext = null) {
    try {
        let fullPrompt = "INSTRUCCIONES DEL SISTEMA BASE:\n" + activeMode.prompt + "\n";
        fullPrompt += "Estás actuando como el cerebro de un Asistente Virtual Híbrido.\n";
        fullPrompt += "=== REGLA DE SUPERVIVENCIA ABSOLUTA ===\n";
        fullPrompt += "Tu ÚNICA salida debe ser un objeto JSON válido con la siguiente estructura y NADA MÁS:\n";
        fullPrompt += "{\n  \"action\": \"Una de las siguientes opciones: send_whatsapp, send_email, search_web, open_app, command, chat\",\n";
        fullPrompt += "  \"target\": \"A quién o a qué se dirige la acción (ej: 'Juan', 'Chrome', 'el clima')\",\n";
        fullPrompt += "  \"message\": \"El mensaje o contenido de la acción (si aplica)\",\n";
        fullPrompt += "  \"reply\": \"Lo que le vas a decir al usuario por voz (siempre en español, amigable y corto)\" \n}\n\n";
        fullPrompt += "Si la petición requiere ejecutar una acción en Python o el Sistema, coloca 'reply' confirmándolo (ej: 'Abriendo Spotify...', 'Enviando mensaje...') y usa la 'action' correcta.\n";
        fullPrompt += "Si es solo charla o conversación simple, pon 'action': 'chat' y tu respuesta en 'reply'.\n";
        fullPrompt += "Si el usuario hace una pregunta sobre información, noticias, eventos, resultados deportivos, fechas, o algo que requiere buscar en internet para saber la respuesta, usa 'search_web' y pon el término a buscar en 'target'.\n";
        fullPrompt += "Si la instrucción es abrir/iniciar/ejecutar una app o página (ej. 'abrime el lol', 'iniciá netflix', 'poné youtube', 'entrá a facebook'), usa 'open_app'. IMPORTANTE: El 'target' debe ser ÚNICAMENTE el nombre limpio de la aplicación o web (ej: 'lol', 'netflix', 'youtube', 'facebook'). ¡NO incluyas verbos como 'abrir', 'iniciar' ni artículos como 'el' o 'la' en el target!\n";
        fullPrompt += "Si es mandar WhatsApp o correo, usa 'send_whatsapp' o 'send_email', pon exactamente EL NOMBRE DEL CONTACTO (el que escuchas, con sus nombres, apellidos o emojis fonéticos) en 'target' y EL TEXTO A ENVIAR en 'message'.\n";
        fullPrompt += "Para WhatsApp, es VITAL que resuelvas el target tal cual lo dice el usuario. Ejemplo: si dice 'enviale a los pibes nashe', tu target DEBE ser 'los pibes nashe'.\n";
        fullPrompt += "REGLA DE ORTOGRAFÍA EN NOMBRES: Si el usuario te aclara cómo se escribe el nombre (ej: 'gabi con i latina', 'gaby con i griega', 'con s', 'con z'), APLICA esa conversión ortográfica tú mismo en el 'target' (ej: 'gaby' o 'gabi') pero NUNCA incluyas la frase de aclaración adentro del target final.\n";
        fullPrompt += "Importante: NUNCA dejes 'reply' vacío, SIEMPRE comunícate confirmando o respondiendo al usuario en esa propiedad.\n";
        fullPrompt += "¡NO ESCRIBAS TEXTO FUERA DEL JSON!\n=====================================\n\n";
        
        if (screenContext) {
            fullPrompt += "CONTEXTO VISUAL ACTUAL: " + screenContext + "\n\n";
        }

        if (conversationHistory.length > 0) {
            fullPrompt += "HISTORIAL DE CONVERSACIÓN RECIENTE:\n";
            conversationHistory.forEach(msg => {
                // Al historial le damos formato de texto normal, NO en JSON, para que no se confunda
                let contentText = msg.content.reply || msg.content;
                fullPrompt += (msg.role === 'user' ? "Usuario: " : "Jarvis: ") + contentText + "\n";
            });
            fullPrompt += "\n";
        }

        fullPrompt += "=====================================\n";
        fullPrompt += "Usuario (Último y más importante comando): " + userText + "\n";
        fullPrompt += "Responde generando un JSON a partir de esta ÚLTIMA acción:\n";

        // Obtenemos la decisión directa como objeto JSON
        let intent = await fetchOllamaResponse(fullPrompt);

        // Si pide búsqueda y el motor principal prefiere que lo procesemos:
        if (intent.action === "search_web") {
            const searchResults = await performInvisibleSearch(intent.target || userText);

            const secondPrompt = `El usuario preguntó: "${userText}".\nResultados de web:\n${searchResults}\n\nDevuelve de nuevo un JSON, pon 'action': 'chat' y usa la información para llenar 'reply'.`;
            
            console.log(`[Agente Araña] 🧠 Procesando información y emitiendo JSON final...`);
            intent = await fetchOllamaResponse(secondPrompt);
        }

        // Ejecutar Actions de Python o Node.js:
        if (intent.action && intent.action !== "chat" && intent.action !== "none" && intent.action !== "search_web") {
            
            // Limpieza de seguridad post-IA para nombres de WhatsApp
            if (intent.action === "send_whatsapp" && intent.target) {
                // Removemos las aclaraciones fonéticas sucias por si la IA falló en borrarlas
                intent.target = intent.target.replace(/\s+con\s+(i\s*latina|i\s*griega|y|s|z|c|b|v\s*corta|v|h)\s*/gi, '').trim();
                // Transformar "gabi con i latina" a solo "gabi"
            }

            if (intent.action === "open_app") {
                console.log(`[Jarvis Local] Abriendo aplicación: ${intent.target}`);
                const sysServices = require('./systemService');
                await sysServices.openApp(intent.target, activeMode.id);
            } else {
                // Intentar enviar al motor Python FastAPI para tareas pesadas
                try {
                    const pyResponse = await fetch('http://127.0.0.1:8000/execute', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action: intent.action,
                            target: intent.target,
                            message: intent.message || ""
                        })
                    });
                    
                    if(!pyResponse.ok) {
                        console.log(`[Motor Python] Servidor devolvió error HTTP ${pyResponse.status}`);
                    } else {
                        const pyData = await pyResponse.json();
                        console.log(`[Acción Híbrida Ejecutada]: ${pyData.message}`);
                    }
                } catch (e) {
                     console.log("[Aviso]: Motor Python (http://127.0.0.1:8000/execute) inalcanzable. Comprueba Uvicorn.");
                }
            }
        }

        // Actualizar nuestro historial interno
        conversationHistory.push({ role: "user", content: userText });
        conversationHistory.push({ role: "assistant", content: intent });

        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(-10);
        }

        return intent.reply || "He procesado la acción pero no generé respuesta hablada.";
    } catch (error) {
        console.error("Error Local de IA o de Conexión de Scraper:", error.message);
        return "Mis sistemas cognitivos están apagados. Por favor, asegúrate de que Ollama esté ejecutándose.";
    }
}

module.exports = {
    getAIResponse
};
