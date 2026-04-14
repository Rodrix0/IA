const fs = require('fs');
let code = fs.readFileSync('./services/aiService.js', 'utf8');

// Buscamos la linea erronea
let errLine = 'console.log([Jarvis Arquitecto] Disenando Indice de Capitulos desde el universo de datos fusionados...);';
code = code.replace(errLine, 'console.log("[Jarvis Arquitecto] Disenando Indice de Capitulos desde el universo de datos fusionados...");');

fs.writeFileSync('./services/aiService.js', code);
