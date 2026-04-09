// Eliminamos las credenciales de Google porque ahora somos 100% locales
let conversationHistory = [];

async function getAIResponse(userText, activeMode, screenContext = null) {
    try {
        // En Ollama, enviamos las instrucciones directamente al motor local
        let fullPrompt = "INSTRUCCIONES DE COMPORTAMIENTO (Debes actuar siempre así):\n" + activeMode.prompt + "\n\n";
        
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

        // Llamada a la API local de Ollama (Corre completamente en tu computadora)
        const response = await fetch('http://127.0.0.1:11434/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'llama3', // Puedes cambiarlo a 'mistral' o 'phi3' si prefieres
                prompt: fullPrompt,
                stream: false
            })
        });

        if (!response.ok) {
            throw new Error(`Ollama devolvió un error HTTP: ${response.status}`);
        }

        const data = await response.json();
        const reply = data.response;

        // Actualizar nuestro historial interno
        conversationHistory.push({ role: "user", content: userText });
        conversationHistory.push({ role: "assistant", content: reply });

        // Mantenemos solo los últimos 10 mensajes
        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(-10);
        }

        return reply;
    } catch (error) {
        console.error("Error Local de IA:", error.message);
        return "Mis sistemas cognitivos están apagados. Por favor, asegúrate de que Ollama esté ejecutándose en tu computadora.";
    }
}

module.exports = {
    getAIResponse
};
