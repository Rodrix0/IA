const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config();

let conversationHistory = [];

function getGeminiClient() {
    const key = process.env.GEMINI_API_KEY;
    if (!key || key === 'tu_api_key_de_gemini_aqui') {
        return null;
    }
    return new GoogleGenerativeAI(key);
}

async function getAIResponse(userText, activeMode) {
    const genAI = getGeminiClient();
    
    if (!genAI) {
        return "El sistema Jarvis no tiene configurada la clave API de Gemini. Por favor, configura el archivo .env en el servidor.";
    }

    try {
        // Usamos el modelo optimizado, puedes cambiarlo a gemini-pro o gemini-1.5-flash
        const model = genAI.getGenerativeModel({ 
            model: "gemini-2.5-flash-lite"
        });

        // Compilamos todo directamente en un gran prompt de texto.
        // Esto funciona de manera 100% segura en CUALQUIER versión de la API y modelo.
        let fullPrompt = "INSTRUCCIONES DE COMPORTAMIENTO (Debes actuar siempre así):\n" + activeMode.prompt + "\n\n";
        
        if (conversationHistory.length > 0) {
            fullPrompt += "HISTORIAL DE CONVERSACIÓN RECIENTE:\n";
            conversationHistory.forEach(msg => {
                fullPrompt += (msg.role === 'user' ? "Usuario" : "Jarvis") + ": " + msg.content + "\n";
            });
            fullPrompt += "\n";
        }

        fullPrompt += "Usuario: " + userText + "\nJarvis:";

        // Llamada simple que funciona universalmente
        const result = await model.generateContent(fullPrompt);
        const response = await result.response;
        const reply = response.text();

        // Actualizar nuestro historial interno

        conversationHistory.push({ role: "user", content: userText });
        conversationHistory.push({ role: "assistant", content: reply });

        // Mantenemos solo los últimos 10 mensajes
        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(-10);
        }

        return reply;
    } catch (error) {
        console.error("Gemini Error:", error);
        return "Hubo un error al procesar mi red neuronal con Gemini. Verifica la conexión a internet o tu clave API.";
    }
}

module.exports = {
    getAIResponse
};
