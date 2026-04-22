const fs = require('fs');
let code = fs.readFileSync('jarvis-app/backend/services/aiService.js', 'utf8');

// 1. Remove the old handlers for search_web and search_internet from the switch/if blocks
const newHandler = `
                } else if (intent.action === 'search_internet' || intent.action === 'search_web') {
                    console.log(\`[Python Router] Redirigiendo consulta fáctica al motor Python (FastAPI)...\`);
                    try {
                        const { handlePythonRouterDecision } = require('./systemService');
                        const pyReq = await fetch('http://127.0.0.1:8000/api/v1/query', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query: userText })
                        });
                        if (pyReq.ok) {
                            const resJson = await pyReq.json();
                            const decision = resJson.data;
                            if (decision.action === 'reply') {
                                intent.message = decision.message + (decision.source ? ' (Fuente: ' + decision.source + ')' : '');
                            } else {
                                intent.message = await handlePythonRouterDecision(decision);
                            }
                        } else {
                            intent.message = "Hubo un error del motor Python comunicándose con los APIs.";
                        }
                    } catch(e) {
                         console.error(e);
                         intent.message = "No pude contactar a la inteligencia híbrida en Python.";
                    }
                    intent.action_type = "speak";
`;

// we need to find where intent.action === 'search_web' is handled
const regexHandlers = /} else if \(\(intent\.action === ['"]search_web['"] \|\| intent\.action === ['"]search_internet['"]\) && targetType\) \{[\s\S]*?\} else if \(intent\.action === ['"]create_document['"]\)/;
// Wait, maybe the logic is longer. Let's just use string replace using split or substrings.
