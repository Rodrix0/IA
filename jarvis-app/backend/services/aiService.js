const cheerio = require('cheerio');

// Eliminamos las credenciales de Google porque ahora somos 100% locales
let conversationHistory = [];

function extractRecipientFromCurrentUtterance(text) {
    if (!text || typeof text !== 'string') return '';

    const cleaned = text
        .trim()
        .replace(/["'`´]+/g, '')
        .replace(/[\u0000-\u001F]/g, ' ')
        .replace(/\s+/g, ' ')
        .replace(/[.!,;:?]+$/g, '');

    // Casos: "manda ... a analistas", "envía ... para analistas"
    const m = cleaned.match(/\b(?:manda(?:r)?|env[ií]a(?:r)?|m[aá]ndale|env[ií]ale?)\b[\s\S]*?\b(?:a|para)\s+([a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ][a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ\s._-]{1,80})$/i);
    if (!m || !m[1]) return '';

    let recipient = m[1].trim();
    recipient = recipient
        .replace(/\b(?:por favor|gracias|porfa|ahora|ya)\b/gi, '')
        .replace(/\s+/g, ' ')
        .trim();

    return recipient;
}

function getLastAssistantReplyFromHistory() {
    for (let i = conversationHistory.length - 1; i >= 0; i--) {
        const msg = conversationHistory[i];
        if (msg.role !== 'assistant') continue;
        if (typeof msg.content === 'string' && msg.content.trim()) return msg.content.trim();
        if (msg.content && typeof msg.content.reply === 'string' && msg.content.reply.trim()) {
            return msg.content.reply.trim();
        }
    }
    return '';
}

function recoverIntentFromBrokenJson(rawText) {
    if (!rawText || typeof rawText !== 'string') return null;

    const cleaned = rawText.replace(/\u0000/g, '').trim();

    // 1) Attempt to parse a likely JSON object slice.
    const firstBrace = cleaned.indexOf('{');
    const lastBrace = cleaned.lastIndexOf('}');
    if (firstBrace !== -1 && lastBrace > firstBrace) {
        const candidate = cleaned.slice(firstBrace, lastBrace + 1);
        try {
            return JSON.parse(candidate);
        } catch (e) {
            // Continue with tolerant extraction.
        }
    }

    // 2) Tolerant regex extraction for malformed/truncated outputs.
    const actionMatch = cleaned.match(/"action"\s*:\s*"([^"]+)"/i);
    const targetMatch = cleaned.match(/"target"\s*:\s*"([\s\S]*?)"\s*(,|\n|\r|$)/i);
    const messageMatch = cleaned.match(/"message"\s*:\s*"([\s\S]*?)"\s*(,|\n|\r|$)/i);
    const replyStart = cleaned.match(/"reply"\s*:\s*"([\s\S]*)$/i);

    if (!actionMatch && !replyStart) return null;

    let reply = replyStart ? replyStart[1] : '';
    reply = reply
        .replace(/\\n/g, '\n')
        .replace(/\\"/g, '"')
        .replace(/[\u0000-\u001F]/g, ' ')
        .replace(/[",\s}]*$/, '')
        .trim();

    return {
        action: actionMatch ? actionMatch[1] : 'chat',
        target: targetMatch ? targetMatch[1].trim() : '',
        message: messageMatch ? messageMatch[1].trim() : '',
        reply: reply || 'No pude estructurar el JSON completo, pero pude recuperar la respuesta principal.'
    };
}

async function performInvisibleSearch(query, maxLength = 3000) {
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
        
        // Le pasamos los caracteres especificados a Llama 3
        if (maxLength > 0) {
            scrapedText = scrapedText.substring(0, maxLength);
        }
        
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
        const recovered = recoverIntentFromBrokenJson(data.response);
        if (recovered) {
            console.warn("[Parser Tolerante] Se recuperó una respuesta utilizable desde JSON inválido.");
            return recovered;
        }
        return {
            action: "chat",
            reply: "No pude estructurar la respuesta en JSON, pero sigo operativo. Repite tu pedido y lo intento de nuevo."
        };
    }
}

async function getAIResponse(userText, activeMode, screenContext = null) {
    try {
        let fullPrompt = "INSTRUCCIONES DEL SISTEMA BASE:\n" + activeMode.prompt + "\n";
        fullPrompt += "Estás actuando como el cerebro de un Asistente Virtual Híbrido.\n";
        fullPrompt += "=== REGLA DE SUPERVIVENCIA ABSOLUTA ===\n";
        fullPrompt += "Tu ÚNICA salida debe ser un objeto JSON válido con la siguiente estructura y NADA MÁS:\n";
        fullPrompt += "{\n  \"action\": \"Una de las siguientes opciones: send_whatsapp, send_email, search_web, open_app, command, schedule_task, check_reminders, clear_reminders, generate_prompt, create_document, chat\",\n";
        fullPrompt += "  \"target\": \"A quién o a qué se dirige la acción (ej: 'informe sobre la ingeniería de sistemas')\",\n";
        fullPrompt += "  \"message\": \"El mensaje o contenido de la acción (si aplica)\",\n";
        fullPrompt += "  \"time\": \"Opcional. SOLO si action es 'schedule_task', pon aquí la hora en formato HH:MM (ej: '14:00')\",\n";
        fullPrompt += "  \"action_type\": \"Opcional. Si action es 'schedule_task' (ej: 'send_whatsapp'). Si action es 'create_document', pon el formato (ej: 'doc', 'excel', 'ppt')\",\n";
        fullPrompt += "  \"reply\": \"Lo que le vas a decir al usuario por voz (siempre en español, amigable y corto)\" \n}\n\n";
        fullPrompt += "Si el usuario TE PIDE CREAR UN INFORME, DOCUMENTO, WORD, EXCEL O PRESENTACIÓN (POWERPOINT) (ej: 'hazme un informe con normas apa sobre ingeniería basándote en este link'), usa 'action': 'create_document'. En 'target' pon el tema y en 'action_type' pon el formato ('doc', 'excel', 'ppt', 'pdf'). IMPORTANTE: Si el usuario te pasa un enlace web (http...) o la ruta de un PDF (.pdf), guárdalo EXACTAMENTE en la propiedad 'message'. Si el usuario te pide que busques la información en Google/Internet por él (ej: 'crea un doc sobre automata buscando en google'), escribe la palabra exacta 'search_web' dentro de 'message'. Si no pide buscar en internet ni te da un archivo, déjala vacía.\n";
        fullPrompt += "Si el usuario TE PIDE CREAR UN PROMPT DETALLADO o FABRICAR UN PROMPT o diseñar una estructura de proyecto/código para abrir en VS Code (ej: 'creá un prompt detallado sobre una página web de turnos'), usa 'action': 'generate_prompt' y en 'target' pon la temática (ej: 'página web de turnos').\n";
        fullPrompt += "Si la petición requiere ejecutar una acción en Python o el Sistema, coloca 'reply' confirmándolo (ej: 'Abriendo Spotify...', 'Enviando mensaje...') y usa la 'action' correcta.\n";
        fullPrompt += "Si el usuario TE PIDE QUE PROGRAMES UNA TAREA A UNA HORA o que mandes un mensaje LUEGO / MÁS TARDE en una hora específica (ej: 'mándale un mensaje a ma a las 14:00'), usa 'action': 'schedule_task'. Llena 'target' con la persona o cosa, 'message' con lo que hay que enviar o decir, 'action_type' con la acción real ('send_whatsapp' o 'speak' o 'open_app'), y 'time' con la hora 'HH:MM'.\n";
        fullPrompt += "Si el usuario pregunta QUÉ TIENE QUE HACER, o SUS TAREAS / RECORDATORIOS (ej: 'qué tengo para hacer hoy', 'revisá mis recordatorios', 'fijate en mi app'), usa la acción 'check_reminders'. Tu 'reply' debe confirmar que lo revisarás.\n";
        fullPrompt += "Si el usuario TE PIDE BORRAR, LIMPIAR O ELIMINAR sus alarmas o tareas locales, usa la acción 'clear_reminders'.\n";
        fullPrompt += "Si es solo charla o conversación simple, pon 'action': 'chat' y tu respuesta en 'reply'.\n";
        fullPrompt += "Si el usuario te hace una PREGUNTA donde TÚ debes contestarle verbalmente con información (ej: 'quién ganó el partido', 'qué es un autómata', 'cuándo juega el real'), usa 'search_web' y pon el conocimiento a buscar en 'target'.\n";
        fullPrompt += "Si el usuario te pide ABRIR, BUSCAR o PONER algo dentro de una aplicación web para que ÉL lo vea (ej: 'abrir chat gpt y buscar conejos', 'abre youtube y pon la cobra', 'busca motos en google'), debes usar 'open_app'. IMPORTANTE: En el 'target', incluye el nombre de la app junto con lo que quiere buscar (ej: 'chat gpt buscar conejos', 'youtube la cobra', 'google comprar motos'). NUNCA uses 'search_web' si el usuario te está pidiendo que abras la página.\n";
        fullPrompt += "Si es simplemente abrir un juego o app nativa limpia (ej: 'abrime el lol', 'iniciá el lol', 'poné el netflix'), usa 'open_app' y pon ÚNICAMENTE el nombre limpio en 'target' sin verbos.\n";
        fullPrompt += "Si es mandar WhatsApp o correo, usa 'send_whatsapp' o 'send_email', pon exactamente EL NOMBRE DEL CONTACTO (el que escuchas, con sus nombres, apellidos o emojis fonéticos) en 'target' y EL TEXTO A ENVIAR en 'message'.\n";
        fullPrompt += "Si el usuario dice 'manda eso', 'con esa información', 'con esa info', 'envía lo anterior' o similares, entonces en 'message' debes copiar literalmente la ÚLTIMA respuesta que tú le diste en la conversación (no inventar ni resumir).\n";
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

        // Fallback determinístico del destinatario según frase ACTUAL del usuario.
        const recipientFromCurrentUtterance = extractRecipientFromCurrentUtterance(userText);
        if ((intent.action === 'send_whatsapp' || intent.action === 'send_email') && recipientFromCurrentUtterance) {
            intent.target = recipientFromCurrentUtterance;
        }

        // Fallback determinístico: si el usuario pide enviar "esa info", tomamos la última respuesta del asistente.
        const asksPreviousInfo = /\b(con\s+esa\s+info(?:rmaci[oó]n)?|manda\s+eso|env[ií]a\s+eso|env[ií]a\s+lo\s+anterior|manda\s+lo\s+anterior|esa\s+informaci[oó]n|esa\s+info)\b/i.test(userText);
        if ((intent.action === 'send_whatsapp' || intent.action === 'send_email') && asksPreviousInfo) {
            const lastReply = getLastAssistantReplyFromHistory();
            if (lastReply) {
                intent.message = lastReply;
            }
        }

        // Si pide búsqueda y el motor principal prefiere que lo procesemos:
        if (intent.action === "search_web") {
            const searchResults = await performInvisibleSearch(intent.target || userText);

            const secondPrompt = `El usuario preguntó: "${userText}".\nResultados de web:\n${searchResults}\n\nResponde EXCLUSIVAMENTE con un JSON válido (sin texto extra) con esta forma:\n{\n  "action": "chat",\n  "reply": "respuesta en español"\n}\nAsegúrate de escapar comillas internas dentro de reply.`;
            
            console.log(`[Agente Araña] 🧠 Procesando información y emitiendo JSON final...`);
            intent = await fetchOllamaResponse(secondPrompt);
        }

        // Ejecutar Actions de Python o Node.js:
        if (intent.action && intent.action !== "chat" && intent.action !== "none" && intent.action !== "search_web") {
            const sysServices = require('./systemService');
            const remServices = require('./reminderService');
            
            // Tareas Programadas y Recordatorios:
            if (intent.action === "schedule_task") {
                if (intent.time && intent.action_type) {
                    remServices.addLocalReminder(intent.time, intent.action_type, intent.target || "", intent.message || "");
                    console.log(`[Jarvis Cronos] ⏰ Nueva Tarea Programada: ${intent.action_type} a las ${intent.time}`);
                    return `Entendido señor, programé la tarea para las ${intent.time}.`;
                } else {
                    return "No comprendí a qué hora debo realizar eso, por favor dímelo otra vez.";
                }
            }

            if (intent.action === "clear_reminders") {
                remServices.clearLocalReminders();
                console.log(`[Jarvis Cronos] 🧹 Reminders locales borrados.`);
                return "He limpiado todas las alarmas y tareas programadas locales de mi sistema.";
            }
            
            if (intent.action === "check_reminders") {
                console.log(`[Jarvis Inteligencia] Consultando base de datos Local y Extrayendo datos de Supabase...`);
                const locales = remServices.getLocalReminders();
                const textoNube = await remServices.fetchExternalTasks(); // <-- Llama a Supabase
                
                let memoryStr = locales.length > 0 
                  ? `Tareas Locales Programadas Activas: ${locales.map(r => `${r.action} a ${r.target} a las ${r.time}`).join(', ')}.` 
                  : "No hay alarmas locales programadas.";
                
                const secondPrompt = `El usuario te pregunta qué cosas tiene para hacer.
                \nSTATUS LOCAL:
                \n${memoryStr}
                \nTAREAS OBTENIDAS DESDE SU BASE DE DATOS EXTERNA (SUPABASE): 
                \n${textoNube}
                \n\nDevuelve un JSON con 'action': 'chat'. En el 'reply', actúa como un asistente elegante y resúmele TODO lo que tiene por hacer, juntando la data local y la externa si aplica. Si dice que faltan credenciales, explícale de forma amigable que debe configurarme el .env con los datos de Supabase.`;
                
                console.log(`[Agente Recordatorios] 🧠 Evaluando datos combinados y emitiendo JSON final...`);
                intent = await fetchOllamaResponse(secondPrompt);
                
                // Actualizamos el historial interno con la deducción final para no romper la cadena
                conversationHistory.push({ role: "user", content: userText });
                conversationHistory.push({ role: "assistant", content: intent });
                return intent.reply;
            }

            // Limpieza de seguridad post-IA para nombres de WhatsApp
            if (intent.action === "send_whatsapp" && intent.target) {
                // Removemos las aclaraciones fonéticas sucias por si la IA falló en borrarlas
                intent.target = intent.target.replace(/\s+con\s+(i\s*latina|i\s*griega|y|s|z|c|b|v\s*corta|v|h)\s*/gi, '').trim();
                // Transformar "gabi con i latina" a solo "gabi"
            }

            if (intent.action === "create_document") {
                const fs = require('fs');
                const path = require('path');
                const { exec } = require('child_process');
                
                console.log(`[Jarvis Office] 📚 Generando documento en formato ${intent.action_type} para: ${intent.target}`);
                
                // --- INYECCIÓN DE CONTEXTO (RAG) MULTIPLE AVANZADO ---
                let contextText = "";
                if (intent.message && intent.message.trim() !== "") {
                    let allChunks = [];
                    // Soportamos separaciones por coma, tubería o espaciados seguidos de unidad.
                    let sourcesList = intent.message.trim().split(/[,|]|\s+(?=http|[a-zA-Z]:\\|\/)/);
                    for (let s of sourcesList) {
                        // Limpiar comillas, comas sueltas, espacios ocultos
                        let source = s.trim().replace(/['",]/g, '').trim(); 
                        if (!source) continue;
                        
                        console.log(`[Jarvis RAG] 🔍 Analizando fuente en profundidad: ${source}`);
                        try {
                            let textExtracted = "";
                            if (source === "search_web") {
                                console.log(`[Jarvis RAG] 🕸️ Investigando en la nube para auto-redactar el doc: "${intent.target}"...`);
                                // Buscamos en Yahoo pero extraemos más texto límite para mejor redacción de la IA
                                const searchRes = await performInvisibleSearch(intent.target, 20000); // 20k ch limit para contexto
                                textExtracted = searchRes || "No hay resultados.";
                            } else if (source.startsWith("http")) {
                                const cheerio = require('cheerio');
                                const res = await fetch(source);
                                const html = await res.text();
                                const $ = cheerio.load(html);
                                $('script, style, noscript, header, footer, nav').remove();
                                textExtracted = $('body').text().replace(/\s+/g, ' '); 
                                console.log(`[Jarvis RAG] ✅ Web cargada en memoria.`);
                            } else if (source.toLowerCase().endsWith(".pdf")) {
                                const pdfParse = require('pdf-parse');
                                if (fs.existsSync(source)) {
                                    const dataBuffer = fs.readFileSync(source);
                                    const pdfData = await pdfParse(dataBuffer);
                                    textExtracted = pdfData.text.replace(/\s+/g, ' ');
                                    console.log(`[Jarvis RAG] ✅ PDF cargado completo: ${textExtracted.length} caracteres leídos.`);
                                } else {
                                    console.log(`[Jarvis RAG] ❌ Archivo PDF no encontrado: ${source}`);
                                }
                            }
                            
                            // Fragmentar el libro/doc en bloques legibles de ~3000 caracteres (aprox 1 hoja)
                            if (textExtracted) {
                                let parts = textExtracted.match(/.{1,3000}(?=\s|$)/g) || [textExtracted];
                                parts.forEach(p => allChunks.push({ text: p, source: source }));
                            }
                        } catch (err) {
                            console.error(`[Jarvis RAG] Error extrayendo ${source}:`, err.message);
                        }
                    }
                    
                    if(allChunks.length > 0) {
                        let totalChars = allChunks.reduce((acc, c) => acc + c.text.length, 0);
                        const charsLimit = 65000; // Capacidad nativa de 16k tokens en Llama 3 (sin truncar)

                        if (totalChars <= charsLimit) {
                            console.log(`[Jarvis RAG] Todo el texto (${totalChars} chars) entra perfectamente en la mente de la IA. Asimilando en orden exacto...`);
                            let currentSrc = "";
                            allChunks.forEach((c, index) => {
                                if (currentSrc !== c.source) {
                                    contextText += `\n\n[--- INICIO DOCUMENTO ORIGINAL: ${c.source} ---]\n`;
                                    currentSrc = c.source;
                                }
                                contextText += c.text + "\n";
                            });
                        } else {
                            console.log(`[Jarvis RAG] Texto excesivo (${totalChars} chars). Filtrando inteligentemente sin romper la cronología...`);
                            let keywords = intent.target.toLowerCase().split(/\s+/).filter(w => w.length > 3);
                            if (keywords.length === 0) keywords = intent.target.toLowerCase().split(/\s+/);
                            
                            allChunks.forEach((chunk, index) => {
                                let score = 0;
                                let lowerText = chunk.text.toLowerCase();
                                keywords.forEach(kw => { if(lowerText.includes(kw)) score += 1; });
                                chunk.score = score;
                                chunk.originalIndex = index; // GUARDAR EL ORDEN CRONOLÓGICO EXACTO
                            });
                            
                            let chunksBySource = {};
                            allChunks.forEach(c => {
                                if (!chunksBySource[c.source]) chunksBySource[c.source] = [];
                                chunksBySource[c.source].push(c);
                            });

                            const sourcesArray = Object.keys(chunksBySource);
                            if(sourcesArray.length > 0) {
                                const charsPerSource = Math.floor(charsLimit / sourcesArray.length);
                                sourcesArray.forEach((src, index) => {
                                    // Primero ordenamos temporalmente por puntuación para quedarnos con los mejores
                                    let bestChunks = chunksBySource[src].sort((a, b) => b.score - a.score);
                                    let selectedChunks = [];
                                    let srcTextLen = 0;

                                    for (let c of bestChunks) {
                                        if (srcTextLen > charsPerSource) break;
                                        selectedChunks.push(c);
                                        srcTextLen += c.text.length;
                                    }

                                    // ¡REGLA DE ORO! Volver a ordenar esos pedazos seleccionados a su orden cronológico original de lectura
                                    selectedChunks.sort((a, b) => a.originalIndex - b.originalIndex);

                                    contextText += `\n\n[--- INICIO FRAGMENTOS IMPORTANTES: ${src} ---]\n`;
                                    selectedChunks.forEach(c => {
                                        contextText += c.text + "\n...\n";
                                    });
                                    console.log(`[Jarvis RAG] ✅ Archivo N.º ${index + 1} ASIMILADO: ${srcTextLen} caracteres en orden cronológico.`);
                                });
                            }
                        }
                        console.log(`[Jarvis RAG] 💡 Contexto GLOBAL inyectado: ${contextText.length} caracteres.`);
                    }
                }
                
                // Generar contenido con IA primero
                let docPrompt = `ERES UN TRANSCRIPTOR TÉCNICO Y CATEDRÁTICO DE INGENIERÍA. Has sido advertido de que estás operando como un 'Resumidor Eficiente', lo cual baja la nota académica. Para subir la nota a la excelencia, tu obligación absoluta es procesar el texto entregado en la memoria actuando puramente como un "TRANSCRIPTOR TÉCNICO".

[METODOLOGÍA DE DESARROLLO OBLIGATORIA]
Paso 1: Lee el "DOCUMENTO ORIGINAL 1" en memoria. Haz una transcripción técnica de todos los temas, modelos lógicos y matemáticas. Explícalos TODOS.
Paso 2: Haz lo mismo con el DOCUMENTO 2, 3, etc., sucesivamente.
Paso 3: ASEGÚRATE de no dejar ningún subtítulo, teorema o técnica afuera. ¡Vuélcalo todo a texto!

[REGLAS ANTI-RESUMEN Y TRANSCRIPCIÓN EXACTA]
- OBLIGACIÓN MATEMÁTICA (MEDIDAS DE DESEMPEÑO): Cada vez que menciones métricas, características operativas o "Medidas de Desempeño", estás OBLIGADO a escribir la fórmula matemática correspondiente (ej: L, Lq, W, Wq, P, etc) en una línea independiente. No lo asumas, escríbelo explícitamente.
- OBLIGACIÓN DE VALIDACIÓN Y NOMBRES: Cada vez que hables de "Validación", "Simulación" o "Pruebas", estás obligado a escribir los nombres específicos (ej. pruebas de bondad, Chi-Cuadrado, teóricos, autores) y definirlos a fondo. 
- DESARROLLO TOTAL: Está sumamente penado hacer el documento sintético. Tienes prohibido usar viñetas rápidas. Cada concepto debe detallarse en un bloque robusto (mínimo 5 líneas por tema) demostrando tu rol de Transcriptor.
- LONGITUD: Extiéndete. Demuestra la complejidad extrema del tema.

[ESTRUCTURA DEL INFORME]
- Introducción Científica
- Transcripción Técnica y Modelos Matemáticos (Fórmulas Obligatorias)
- Nombres de Pruebas de Validación y Herramientas
- Conclusión

[ENTREGA]: Genera la obra COMPLETA, PROFUNDAMENTE DESARROLLADA como Transcriptor Técnico. Comienza de inmediato.
`;
                if (contextText) {
                    docPrompt += `${contextText}\n\n`;
                }
                docPrompt += `--- FIN DEL CONTENIDO EN MEMORIA ---
                
Por favor, redacta el informe académico EXTREMADAMENTE EXTENSO basándote ÚNICA Y EXCLUSIVAMENTE en la información de arriba, barriendo todos los conceptos. ¡SIN ESQUELETOS, SIN RESÚMENES, COMPLETO!`;

                try {
                    // Truco Definitivo (RAW Forcing Format)
                    let rawLlama3Prompt = `<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nEres un motor académico puro. Tu objetivo es generar informes técnicos larguísimos y exhaustivos. REGLA SUPREMA: PROHIBIDO RESUMIR y PROHIBIDO OMITIR TEMAS. Todo debe estar copiado, expandido y explicado al máximo detalle matemático.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n${docPrompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\nPor supuesto, comprendo la indicación crítica. A continuación desarrollo el informe técnico académico en profundidad máxima, recorriendo todos los documentos en orden para no dejar NINGÚN tema o fórmula afuera, y garantizando un texto extremadamente rico y extenso:\n\n# Informe Técnico Avanzado\n## Introducción y Marco Teórico\n`;

                    const aiResp = await fetch('http://127.0.0.1:11434/api/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        dispatcher: new (require('undici').Agent)({ headersTimeout: 30 * 60 * 1000 }), // 30 Minutos Timeout
                        body: JSON.stringify({ 
                            model: 'llama3.1', 
                            prompt: rawLlama3Prompt, 
                            raw: true, // CLAVE: Llama 3 directo al formato
                            stream: false,
                            options: {
                                num_ctx: 16384,
                                num_predict: 8192, 
                                temperature: 0.15
                            }
                        })
                    });
                    const aiData = await aiResp.json();
                    let generatedContent = aiData.response;
                    
                    const fileNameBase = `Doc_${intent.target.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30)}_${Date.now()}`;
                    const os = require('os');
                    const targetDir = 'C:\\Users\\Rodrigo\\Desktop\\Generado';
                    if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
                    
                    let finalPath = "";
                    let commandToOpen = "";

                    if (intent.action_type === "doc") {
                        const { Document, Packer, Paragraph, TextRun } = require('docx');
                        
                        // Crear documento de Word simple dividiendo por líneas
                        const lines = generatedContent.split('\n');
                        const children = lines.map(line => new Paragraph({ children: [new TextRun(line)] }));
                        
                        const doc = new Document({
                            sections: [{ properties: {}, children: children }]
                        });
                        
                        finalPath = path.join(targetDir, `${fileNameBase}.docx`);
                        const buffer = await Packer.toBuffer(doc);
                        fs.writeFileSync(finalPath, buffer);
                        commandToOpen = process.platform === 'win32' ? `start "" "${finalPath}"` : `open "${finalPath}"`;
                        
                    } else if (intent.action_type === "ppt") {
                        const pptxgen = require('pptxgenjs');
                        let pptx = new pptxgen();
                        
                        // Dividir por bloques (ej: "Diapositiva X:" generado por la IA)
                        const slidesRaw = generatedContent.split(/(?:Diapositiva \d+:?|\n\n)/i).filter(s => s.trim().length > 0);
                        
                        slidesRaw.forEach(slideText => {
                            let slide = pptx.addSlide();
                            // Agregar texto, centrado
                            slide.addText(slideText.trim().substring(0, 500), { x: 0.5, y: 0.5, w: '90%', h: '90%', fontSize: 18, color: "363636", align: pptx.AlignH.center });
                        });
                        
                        finalPath = path.join(targetDir, `${fileNameBase}.pptx`);
                        await pptx.writeFile({ fileName: finalPath });
                        commandToOpen = process.platform === 'win32' ? `start "" "${finalPath}"` : `open "${finalPath}"`;
                        
                    } else if (intent.action_type === "excel") {
                        const xlsx = require('xlsx');
                        
                        // Intentar parsear las líneas de tabla (ej: col1 | col2 | col3)
                        const lines = generatedContent.split('\n').filter(line => line.trim().length > 0);
                        const aoa = lines.map(line => line.split('|').map(cell => cell.trim()));
                        
                        const ws = xlsx.utils.aoa_to_sheet(aoa);
                        const wb = xlsx.utils.book_new();
                        xlsx.utils.book_append_sheet(wb, ws, "Hoja1");
                        
                        finalPath = path.join(targetDir, `${fileNameBase}.xlsx`);
                        xlsx.writeFile(wb, finalPath);
                        commandToOpen = process.platform === 'win32' ? `start "" "${finalPath}"` : `open "${finalPath}"`;
                    } else if (intent.action_type === "pdf") {
                        const PDFDocument = require('pdfkit');
                        const doc = new PDFDocument();
                        finalPath = path.join(targetDir, `${fileNameBase}.pdf`);
                        
                        const stream = fs.createWriteStream(finalPath);
                        doc.pipe(stream);
                        doc.fontSize(12).text(generatedContent, { align: 'justify' });
                        doc.end();
                        
                        // Esperar a que el archivo se guarde y cierre completamente en el disco
                        await new Promise(resolve => stream.on('finish', resolve));
                        
                        commandToOpen = process.platform === 'win32' ? `start "" "${finalPath}"` : `open "${finalPath}"`;
                    } else {
                        // Fallback a txt si action no está bien
                        finalPath = path.join(targetDir, `${fileNameBase}.txt`);
                        fs.writeFileSync(finalPath, generatedContent, 'utf8');
                        commandToOpen = process.platform === 'win32' ? `start "" "${finalPath}"` : `open "${finalPath}"`;
                    }
                    
                    console.log(`[Jarvis Office] 📄 Archivo listo: ${finalPath}`);
                    exec(commandToOpen, (err) => {
                        if (err) console.error("No se pudo abrir el documento:", err);
                    });
                    
                    conversationHistory.push({ role: "user", content: userText });
                    conversationHistory.push({ role: "assistant", content: intent });
                    return intent.reply || `He generado tu documento sobre ${intent.target} y lo he abierto.`;

                } catch (e) {
                    console.error("Error generando el documento:", e);
                    return "Hubo un fallo generando el archivo Office pedido.";
                }
            }

            if (intent.action === "generate_prompt") {
                const fs = require('fs');
                const path = require('path');
                const { exec } = require('child_process');
                
                console.log(`[Jarvis Prompt Engineer] ✍️ Generando documento detallado para: ${intent.target}`);
                
                // Pedimos a Ollama que redacte un prompt bien detallado
                const pPrompt = `El usuario quiere que escribas un prompt increíblemente detallado, profesional y estructurado sobre: "${intent.target}".\nActúa como un experto en ingeniería de software. Escribe TODO el contenido del prompt en formato Markdown (arquitectura, tecnologías frontend/backend, paso a paso, buenas prácticas, etc).\nIMPORTANTE: No uses introducciones, no devuelvas JSON. Solo devuelve el Markdown puro.`;
                
                try {
                    const promptResponse = await fetch('http://127.0.0.1:11434/api/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            model: 'llama3', 
                            prompt: pPrompt,
                            stream: false
                        })
                    });
                    const promptData = await promptResponse.json();
                    let promptDoc = promptData.response;
                    
                    const os = require('os');
                    const fileName = `Prompt_${intent.target.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.md`;
                    const targetDir = 'C:\\Users\\Rodrigo\\Desktop\\Generado';
                    const filePath = path.join(targetDir, fileName);
                    
                    if (!fs.existsSync(targetDir)) {
                        fs.mkdirSync(targetDir, { recursive: true });
                    }
                    
                    fs.writeFileSync(filePath, promptDoc, 'utf8');
                    console.log(`[Jarvis Prompt Engineer] 📄 Documento creado en: ${fileName}`);
                    
                    // Abrir en VS Code usando el comando code
                    exec(`code "${filePath}"`, (err) => {
                        if (err) console.error("No se pudo abrir VS Code:", err);
                    });
                    
                    conversationHistory.push({ role: "user", content: userText });
                    conversationHistory.push({ role: "assistant", content: intent });
                    if (conversationHistory.length > 10) conversationHistory = conversationHistory.slice(-10);
                    
                    return intent.reply || `He generado el prompt sobre ${intent.target} y lo he abierto en Visual Studio Code.`;
                } catch (e) {
                    console.error("Error generando el prompt:", e);
                    return "Hubo un error al intentar generar el archivo de prompt.";
                }
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
