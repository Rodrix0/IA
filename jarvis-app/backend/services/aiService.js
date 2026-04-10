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
            stream: false
        })
    });

    if (!response.ok) {
        throw new Error(`Ollama devolvió un error HTTP: ${response.status}`);
    }

    const data = await response.json();
    return data.response;
}

async function getAIResponse(userText, activeMode, screenContext = null) {
    try {
        // En Ollama, enviamos las instrucciones directamente al motor local
        let fullPrompt = "INSTRUCCIONES DE COMPORTAMIENTO (Debes actuar siempre así):\n" + activeMode.prompt + "\n";
        fullPrompt += "=== REGLA DE SUPERVIVENCIA ABSOLUTA ===\nSi te preguntan CUALQUIER DATO DEL MUNDO EXTERIOR (clima, cuándo juegan equipos de fútbol, noticias, o definiciones de cosas que no sabes explicar), ESTÁ PROHIBIDO improvisar o usar etiquetas raras (como [FUTBOL] o [JARVIS_OS]). Tu única respuesta debe comenzar obligatoriamente con la frase exacta 'BUSCAR_EN_INTERNET: ' seguida de lo que hay que buscar en Google. \nEjemplo correcto: BUSCAR_EN_INTERNET: cuando juega boca juniors\nEjemplo correcto: BUSCAR_EN_INTERNET: que es la simulacion\n¡No escribas nada más!\n=====================================\n\n";
        
        // Si el observador de pantalla detectó en qué andas metido:
        if (screenContext) {
            fullPrompt += screenContext + "\n\n";
        }

        if (conversationHistory.length > 0) {
            fullPrompt += "HISTORIAL DE CONVERSACIÓN RECIENTE:\n";
            conversationHistory.forEach(msg => {
                fullPrompt += (msg.role === 'user' ? "Usuario" : "Jarvis") + ": " + msg.content + "\n";
            });
            fullPrompt += "\n";
        }

        fullPrompt += "Usuario: " + userText + "\nJarvis:";

        // 1. Primer intento: Preguntarle a la Inteligencia Artificial si lo sabe
        let reply = await fetchOllamaResponse(fullPrompt);

        // 2. ¿El LLM decidió que necesita buscar en internet o está alucinando una etiqueta?
        if (reply.includes("BUSCAR_EN_INTERNET:") || (reply.startsWith("[") && reply.endsWith("]"))) {
            let searchQuery = "";
            
            if (reply.includes("BUSCAR_EN_INTERNET:")) {
                searchQuery = reply.split("BUSCAR_EN_INTERNET:")[1].trim();
            } else {
                // Si la IA desobedece y sigue alucinando corchetes (ej: [JUEGOS_DE_FUTBOL]), le extraemos el texto y buscamos eso
                const match = reply.match(/\[(.*?)\]/);
                if (match && match[1]) {
                    // Limpiamos los "TAGS:" que inventa a veces
                    searchQuery = match[1].replace(/^.*?:\s*/, '').trim();
                    // Si el corchete no dice nada coherente, usamos la pregunta original como búsqueda
                    if (searchQuery.length < 3 || searchQuery.includes("_")) {
                        searchQuery = userText;
                    }
                }
            }
            
            if (searchQuery) {
                // Ejecutamos el Scraper de manera invisible
                const searchResults = await performInvisibleSearch(searchQuery);

                // Volvemos a inyectar la info y le decimos a la IA que nos responda leyendo esto
                const secondPrompt = `Te preguntaron: "${userText}".\nHice una búsqueda en Google y encontré los siguientes datos:\n\n${searchResults}\n\nREGLA: Responde directo, amigable y muy corto a lo que el usuario preguntó utilizando ÚNICAMENTE la información anterior. Si la información no responde perfectamente, deduce la mejor respuesta posible en base a lo encontrado. No repitas la palabra WEB_SEARCH.`;
                
                console.log(`[Agente Araña] 🧠 Leyendo hallazgos de internet y formulando respuesta...`);
                reply = await fetchOllamaResponse(secondPrompt);
            }
        }

        // Actualizar nuestro historial interno
        conversationHistory.push({ role: "user", content: userText });
        conversationHistory.push({ role: "assistant", content: reply });

        // Mantenemos solo los últimos 10 mensajes
        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(-10);
        }

        return reply;
    } catch (error) {
        console.error("Error Local de IA o de Conexión de Scraper:", error.message);
        return "Mis sistemas cognitivos están apagados. Por favor, asegúrate de que Ollama esté ejecutándose en tu computadora.";
    }
}

module.exports = {
    getAIResponse
};
