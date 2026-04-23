const text = "cuando juega boca";
fetch("http://localhost:11434/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        model: "hermes3:8b",
        messages: [
            { role: "system", content: "Eres Jarvis, el asistente de PC." },
            { role: "user", content: text }
        ],
        tools: [
            { type: "function", function: { name: "search_web", description: "Busca en internet datos fácticos (clima, biografías, significado de palabras, resultados deportivos)", parameters: { type: "object", properties: { target: { type: "string" } }, required: ["target"] } } },
            { type: "function", function: { name: "search_internet", description: "USA ESTA CADA VEZ QUE PIDAN: Deportes.", parameters: { type: "object", properties: { target: { type: "string" }, message: { type: "string" } }, required: ["target", "message"] } } },
            { type: "function", function: { name: "chat_casual", description: "Obligatorio: usar para charla", parameters: { type: "object", properties: { reply: { type: "string" } }, required: ["reply"] } } }
        ],
        stream: false
    })
}).then(r => r.json()).then(d => console.log(JSON.stringify(d.message, null, 2)));
