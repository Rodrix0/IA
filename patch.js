const fs = require('fs');
let c = fs.readFileSync('jarvis-app/backend/services/aiService.js', 'utf8');

const s = c.indexOf('{ type: "function", function: { name: "search_web"');
const e = c.indexOf('}, required: ["target"] } } },', s);

if (s !== -1 && e !== -1) {
  const repl = '{ type: "function", function: { name: "search_web", description: "OBLIGATORIA. Úsala SIEMPRE que te pidan sobre RESULTADOS DEPORTIVOS (quién juega, cuándo, cómo salieron, tablas), CLIMA, CRIPTO, DÓLAR, o NOTICIAS ACTUALES. ESTA ES TU FUENTE DE BÚSQUEDA EXCLUSIVA. NUNCA respondas con chat_casual para estos temas ni ninguna otra porque ESTA ES LA UNICA FORMA de que te enteres de los datos de internet. SI NO LA USAS NO SABRAS NADA DEL BOCA JUNIOR. USA ESTO.", parameters: { type: "object", properties: { target: { type: "string", description: "La consulta a buscar en google." } }';
  c = c.substring(0, s) + repl + c.substring(e);
  fs.writeFileSync('jarvis-app/backend/services/aiService.js', c);
  console.log("Patched clean!");
} else {
  console.log("Could not find string ranges.", s, e);
}
