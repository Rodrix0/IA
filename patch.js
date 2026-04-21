const fs = require('fs');
let code = fs.readFileSync('jarvis-app/backend/services/aiService.js', 'utf8');

// 1. Remove WhatsApp Regex overrides
code = code.replace(/const recipientFromCurrentUtterance = extractRecipientFromCurrentUtterance\(userText\);\s*if \(\(intent\.action === 'send_whatsapp' \|\| intent\.action === 'send_email'\) && asksPreviousInfo\) \{\s*const lastReply = getLastAssistantReplyFromHistory\(\);\s*if \(lastReply\) intent\.message = lastReply;\s*\}\s*if \(\(intent\.action === 'send_whatsapp' \|\| intent\.action === 'send_email'\) && recipientFromCurrentUtterance\) \{\s*intent\.target = recipientFromCurrentUtterance;\s*\}/g, 'if ((intent.action === \'send_whatsapp\' || intent.action === \'send_email\') && asksPreviousInfo) { const lastReply = getLastAssistantReplyFromHistory(); if (lastReply) intent.message = lastReply; }');

code = code.replace(/const messageFromUtterance = extractMessageFromCurrentUtterance\(userText\);\s*const recipient = intent\.target \|\| extractRecipientFromCurrentUtterance\(userText\);\s*intent\.action = 'schedule_task';\s*intent\.time = explicitTime;\s*intent\.action_type = actionType;\s*intent\.target = recipient \|\| '';\s*intent\.message = messageFromUtterance \|\| intent\.message \|\| '';/g, 'intent.action = \'schedule_task\'; intent.time = explicitTime; intent.action_type = actionType;');

// 2. Fix [object Object] crash stringify
code = code.replace(/let query = intent\.message \|\| intent\.query \|\| userText;/g, 'let query = (typeof intent.message === "object" ? JSON.stringify(intent.message) : intent.message) || intent.query || userText;');
code = code.replace(/target: intent\.target,/g, 'target: typeof intent.target === "object" ? JSON.stringify(intent.target) : intent.target,');
code = code.replace(/message: intent\.message \|\| ""/g, 'message: typeof intent.message === "object" ? JSON.stringify(intent.message) : intent.message || ""');

// 3. Update AI tool description
code = code.replace(/\{ type: "function", function: \{ name: "generate_prompt",([^}]+)required: \["target", "reply"\] \} \} \},/g, '{ type: "function", function: { name: "generate_prompt", description: "Genera una arquitectura extensa de sistema o un prompt de software. Úsala para crear el contenido de programacion a solicitud del usuario.", parameters: { type: "object", properties: { target: { type: "string", description: "El tema exacto que el usuario solicita para el prompt de software" }, reply: { type: "string", description: "Respuesta hablada" } }, required: ["target", "reply"] } } },');

// 4. Update pPrompt EXACTLY by regex using proper characters
code = code.replace(/const pPrompt = `El usuario quiere que escribas un prompt incre[^`]+Markdown puro.`;/g, 'const pPrompt = `El usuario te ha pedido el siguiente sistema de software:\\n${userText}\\n\\nActúa como Arquitecto de Software y Product Manager Senior.\\nEscribe TODO el contenido del PROMPT MAESTRO en formato Markdown que describa a la perfección lo que hay que programar.\\nIncluye: Objetivo del producto, Descripción de Vistas Web/App, Modelo de Base de Datos propuesto, Lógica del Backend (Endpoints Principales), Stack Tecnológico propuesto, y el Paso a Paso para la IA que lo vaya a codificar.\\nIMPORTANTE: No uses saludos ni introducciones, empieza directamente con el título Markdown (con #). No devuelvas JSON.`;');

fs.writeFileSync('jarvis-app/backend/services/aiService.js', code);
console.log("DONE CLEANLY");
