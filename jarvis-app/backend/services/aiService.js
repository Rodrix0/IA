const cheerio = require('cheerio');

// Eliminamos las credenciales de Google porque ahora somos 100% locales
let conversationHistory = [];

// Funciones legacy limpiadas porque ahora usamos Native Tool Calling a través del LLM.

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
    console.log(`\n[Agente Araña] 🕸️ Infiltrando motor de búsqueda (DuckDuckGo) para: "${query}"...`);
    try {
        const response = await fetch(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        });
        
        const html = await response.text();
        const $ = cheerio.load(html);
        
        $('script, style, noscript, header, footer, svg, img, button').remove();
        
        let scrapedText = $('.result__snippet').text() || $('body').text();
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

async function executeLlamaChat(messages, tools = null, jsonFormat = false) {
    const payload = {
        model: 'llama3.1', // Cambiado a 3.1 para soportar las tools nativas de Ollama
        messages: messages,
        stream: false
    };
    
    if (tools) {
        payload.tools = tools;
    }
    
    if (jsonFormat) {
        payload.format = "json";
    }

    const response = await fetch('http://127.0.0.1:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`Ollama devolvió un error HTTP: ${response.status}`);
    }

    const data = await response.json();
    return data.message;
}

// Mantenemos esto como un wrapper para las llamadas legacy (buscar clima en internet, etc)
async function fetchOllamaResponse(prompt) {
    const msgs = [{ role: "user", content: prompt }];
    try {
        const aiMsg = await executeLlamaChat(msgs, null, true); // true for json
        return JSON.parse(aiMsg.content);
    } catch (e) {
        console.error("Error parseando respuesta JSON de Ollama (Legacy wrapper):", e);
        const recovered = recoverIntentFromBrokenJson(""); 
        return recovered || {
            action: "chat",
            reply: "No pude estructurar la respuesta en JSON, pero sigo operativo. Repite tu pedido y lo intento de nuevo."
        };
    }
}

async function getAIResponse(userText, activeMode, screenContext = null) {
    try {
        let systemPrompt = "INSTRUCCIONES DEL SISTEMA BASE:\n" + activeMode.prompt + "\n";
        systemPrompt += "Eres Jarvis, el asistente de PC. Tienes herramientas de automatización y de auto-aprendizaje (Code-Act).\n";
        systemPrompt += "REGLA DE VIDA O MUERTE: Si el usuario te hace charla casual, te pregunta qué sabes hacer, cómo estás, o cualquier pregunta general sobre ti mismo, ESTÁ EXTRICTAMENTE PROHIBIDO (PENADO) USAR UNA HERRAMIENTA. Responde únicamente chateando de forma natural.\n";
        systemPrompt += "REGLA DE WHATSAPP: El destinatario debe ser el nombre del contacto limpio. Si te piden enviar algo que acabas de explicar o buscar (información anterior), usa tu memoria para escribir toda esa info completa en el campo 'message'.\n";
        
        const dateNow = new Date();
        systemPrompt += `\nFECHA Y HORA ACTUAL DEL SISTEMA: ${dateNow.toLocaleString('es-AR')}. Usa esta información exacta si el usuario pregunta la hora o el día. Si el usuario pregunta la hora de otro país, calcúlala usando tu propio conocimiento horario.\n\n`;

        if (screenContext) {
            systemPrompt += "CONTEXTO VISUAL ACTUAL: " + screenContext + "\n\n";
        }

        let messages = [ { role: "system", content: systemPrompt } ];

        if (conversationHistory.length > 0) {
            conversationHistory.forEach(msg => {
                let contentText = typeof msg.content === 'object' 
                    ? (typeof msg.content.reply === 'string' ? msg.content.reply : JSON.stringify(msg.content.reply || msg.content)) 
                    : String(msg.content);
                messages.push({ role: msg.role, content: contentText });
            });
        }

        messages.push({ role: "user", content: userText });

        const tools = [
            { type: "function", function: { name: "send_whatsapp", description: "Envía un mensaje de WhatsApp a un contacto.", parameters: { type: "object", properties: { target: { type: "string", description: "El nombre exacto del contacto (ej. gabi, mama)" }, message: { type: "string", description: "El contenido exacto a enviar. IMPORTANTE: Si el usuario te pide enviar 'esa info' o 'lo anterior', OBLIGATORIAMENTE debes buscar la informacion detallada en el historial y pegarla aquí COMPLETA." }, reply: { type: "string", description: "Lo que dirás en voz alta" } }, required: ["target", "message", "reply"] } } },
            { type: "function", function: { name: "send_email", description: "Envía un correo electrónico.", parameters: { type: "object", properties: { target: { type: "string", description: "Nombre o dirección" }, message: { type: "string", description: "El contenido exacto a enviar (reemplaza 'esta info' por la data real del historial)." }, reply: { type: "string", description: "Respuesta hablada" } }, required: ["target", "message", "reply"] } } },
            { type: "function", function: { name: "search_web", description: "Busca en internet datos fácticos (clima, clima local, biografías, significado de palabras, resultados deportivos). NUNCA LO USES PARA CONSULTAR LA HORA NI EL DÍA, JAMÁS (usa tu sistema horario local para eso).", parameters: { type: "object", properties: { target: { type: "string", description: "La consulta a buscar en google" } }, required: ["target"] } } },
            { type: "function", function: { name: "open_app", description: "Abre una aplicación web o instalada en la PC (Netflix, LOL, Youtube, Spotify, chat gpt).", parameters: { type: "object", properties: { target: { type: "string", description: "Nombre de la app limpia (ej: 'netflix', 'youtube la cobra')" }, reply: { type: "string", description: "Respuesta hablada confirmando" } }, required: ["target", "reply"] } } },
            { type: "function", function: { name: "schedule_task", description: "Programa una tarea futura a una hora indicada.", parameters: { type: "object", properties: { time: { type: "string", description: "Hora en formato HH:MM (ej. 14:00)" }, action_type: { type: "string", description: "'send_whatsapp', 'speak', o 'open_app'" }, target: { type: "string", description: "A quién va dirigido" }, message: { type: "string", description: "El mensaje a enviar/decir" }, reply: { type: "string", description: "Confirmación en voz alta" } }, required: ["time", "action_type", "reply"] } } },
            { type: "function", function: { name: "check_reminders", description: "Revisa las tareas a realizar o recordatorios activos hoy.", parameters: { type: "object", properties: { reply: { type: "string", description: "Frase de confirmación de que vas a buscar la info" } }, required: ["reply"] } } },
            { type: "function", function: { name: "clear_reminders", description: "Limpia y borra todas las alarmas o tareas programadas.", parameters: { type: "object", properties: { reply: { type: "string", description: "Frase confirmando borrado" } }, required: ["reply"] } } },
            { type: "function", function: { name: "create_document", description: "Genera un informe, Word, Excel, PowerPoint o PDF ultra detallado basandote en links o temas. NO lo uses si piden un prompt o un codigo de software.", parameters: { type: "object", properties: { target: { type: "string", description: "Tema del documento" }, action_type: { type: "string", enum: ["doc", "excel", "ppt", "pdf"], description: "Formato" }, message: { type: "string", description: "Fuentes: URLs o 'search_web'" }, reply: { type: "string", description: "Respuesta hablada" } }, required: ["target", "action_type", "reply"] } } },
            { type: "function", function: { name: "generate_prompt", description: "MÁS IMPORTANTE: NUNCA USES ESTO SI EL USUARIO CHARLA O PREGUNTA QUÉ PUEDES HACER. Genera una arquitectura extensa de sistema. USAR SOLO SÍ PIDEN 'crear prompt de software'.", parameters: { type: "object", properties: { target: { type: "string", description: "La temática" }, reply: { type: "string", description: "Respuesta hablada" } }, required: ["target", "reply"] } } },
            { type: "function", function: { name: "develop_new_skill", description: "CREA SCRIPTS DE PYTHON INTERNOS. ÚSALA SÓLO si el usuario usa las palabras mágicas 'aprende al...', 'quiero que aprendas a...', o 'escribe un script para mi sistema que...'. Te sirve para aprender a hacer tareas de PC que no sabes (ej: 'Aprende a apagar la pc', 'Aprende a sumar dados').", parameters: { type: "object", properties: { target: { type: "string", description: "El objetivo detallado del script que vas a programar en Python para cumplir la habilidad" }, reply: { type: "string", description: "Lo que le dirás repitiendo su orden (ej: 'Comenzando a desarrollar habilidad para bla bla')" } }, required: ["target", "reply"] } } },
            { type: "function", function: { name: "chat_casual", description: "Obligatorio: USAR ESTA HERRAMIENTA SIEMPRE QUE EL USUARIO HAGA CHARLA CASUAL, PREGUNTE LA HORA, EL DÍA, O PIDA TUS CAPACIDADES. Evita errores usando esto.", parameters: { type: "object", properties: { reply: { type: "string", description: "Respuesta conversacional natural al usuario calculada usando tu propio cerebro" } }, required: ["reply"] } } }
        ];

        try {
            const pythonSkillsRes = await fetch('http://127.0.0.1:8000/list_skills');
            if (pythonSkillsRes.ok) {
                const pythonSkills = await pythonSkillsRes.json();
                pythonSkills.forEach(skill => {
                    tools.push({
                        type: "function",
                        function: {
                            name: skill.name,
                            description: skill.description,
                            parameters: skill.parameters
                        }
                    });
                });
            }
        } catch (e) {
            console.error("[Code-Act] No se pudieron cargar habilidades dinámicas de Python:", e.message);
        }

        let llamaResponse = await executeLlamaChat(messages, tools, false);
        
        // Emulamos el intent structure legacy para no quebrar el resto del código
        let intent = {
            action: "chat",
            target: "",
            message: "",
            time: "",
            action_type: "",
            reply: ""
        };

        if (llamaResponse.tool_calls && llamaResponse.tool_calls.length > 0) {
            const tool = llamaResponse.tool_calls[0].function;
            intent.action = tool.name;
            const args = tool.arguments || {};
            intent.target = args.target || "";
            intent.message = args.message || "";
            intent.time = args.time || "";
            intent.action_type = args.action_type || "";
            intent.reply = typeof args.reply === 'string' ? args.reply : (args.reply ? JSON.stringify(args.reply) : "Procediendo con la acción.");
        } else {
            intent.reply = typeof llamaResponse.content === 'string' ? llamaResponse.content : (llamaResponse.content ? JSON.stringify(llamaResponse.content) : "Entendido.");
        }

        // Eliminar fallback de recipient determinístico para dejar que Tool Calling de Llama 3.1 se encargue 100% de parsear el contacto y el mensaje exacto.

        // Si pide búsqueda y el motor principal prefiere que lo procesemos:
        if (intent.action === "search_web") {
            const searchResults = await performInvisibleSearch(intent.target || userText);

            const secondPrompt = `El usuario preguntó: "${userText}".\nResultados de web:\n${searchResults}\n\nResponde como un asistente virtual amigable. Genera ÚNICAMENTE lo que debo decir en voz alta para responder la pregunta, basándote en esos resultados web. SIN formato JSON. Nunca digas que la info es parcial, da lo mejor con lo que hay.`;
            
            console.log(`[Agente Araña] 🧠 Procesando resultados y emitiendo respuesta hablada...`);
            const subMsgs = [{ role: "user", content: secondPrompt }];
            const aiMsg = await executeLlamaChat(subMsgs, null, false);
            intent.reply = aiMsg.content;
        }

        // Ejecutar Actions de Python o Node.js:
        if (intent.action && intent.action !== "chat" && intent.action !== "chat_casual" && intent.action !== "none" && intent.action !== "search_web") {
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
                \nSTATUS LOCAL:\n${memoryStr}
                \nTAREAS DESDE SUPABASE:\n${textoNube}
                \n\nResponde como un asistente virtual elegante. Genera ÚNICAMENTE el texto que debo decir en voz alta resumiendo TODO lo que tiene por hacer, juntando la data local y la externa si aplica. NO USES JSON, NO USES LISTAS COMPLEJAS. Contesta como si estuvieras hablando. Si faltan credenciales, explícale que configure el .env de Supabase.`;
                
                console.log(`[Agente Recordatorios] 🧠 Evaluando datos combinados y emitiendo resumen hablado...`);
                const subMsgs = [{ role: "user", content: secondPrompt }];
                const aiMsg = await executeLlamaChat(subMsgs, null, false);
                intent.reply = aiMsg.content;
                
                // Actualizamos el historial interno con la deducción final para no romper la cadena
                conversationHistory.push({ role: "user", content: userText });
                conversationHistory.push({ role: "assistant", content: intent });
                return typeof intent.reply === 'string' ? intent.reply : JSON.stringify(intent.reply);
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

            if (intent.action === "develop_new_skill") {
                const objective = intent.target || intent.message || userText;
                console.log(`[Code-Act] Enviando a Python orden de desarrollar habilidad: ${objective}`);
                try {
                    await fetch('http://127.0.0.1:8000/develop_skill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ objective: objective })
                    });
                } catch(e) { 
                    console.error("[Code-Act] Python inalcanzable para develop_skill", e);
                }
                
                conversationHistory.push({ role: "user", content: userText });
                conversationHistory.push({ role: "assistant", content: intent });
                return intent.reply || "He iniciado el desarrollo de esta habilidad en segundo plano profundo.";
            }

            if (intent.action.startsWith("skill_")) {
                console.log(`[Code-Act] Ejecutando habilidad aprendida dinámicamente: ${intent.action}`);
                try {
                     const kwargsObj = {};
                     if (intent.target) kwargsObj["kwargs_str"] = typeof intent.target === 'object' ? JSON.stringify(intent.target) : String(intent.target);
                     
                     const reqBody = { skill_name: intent.action, kwargs: kwargsObj };
                     const executeRes = await fetch('http://127.0.0.1:8000/execute_skill', {
                         method: 'POST',
                         headers: { 'Content-Type': 'application/json' },
                         body: JSON.stringify(reqBody)
                     });
                     
                     if (executeRes.ok) {
                         const execData = await executeRes.json();
                         console.log(`[Code-Act] Habilidad ejecutada:`, execData);
                         if (execData.status === "success") {
                             intent.reply = `Hecho. El resultado es: ${execData.result}`;
                         } else {
                             intent.reply = `Lo intenté, pero la habilidad falló: ${execData.message}`;
                         }
                     } else {
                         intent.reply = "La habilidad existe pero el motor Python devolvió error HTTP.";
                     }
                 } catch(e) {
                     intent.reply = "No pude conectarme al motor de habilidades Python.";
                 }
                 
                 conversationHistory.push({ role: "user", content: userText });
                 conversationHistory.push({ role: "assistant", content: intent });
                 return intent.reply;
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
