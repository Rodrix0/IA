const fs = require('fs');
let code = fs.readFileSync('jarvis-app/backend/services/systemService.js', 'utf8');

const newCode = `
// --- 4. Python Router Handler ---
async function handlePythonRouterDecision(decisionJson) {
    if (decisionJson.action === 'reply') {
        const sourceTxt = decisionJson.source ? ' (Fuente: ' + decisionJson.source + ')' : '';
        return decisionJson.message + sourceTxt;
    } 
    else if (decisionJson.action === 'open_app') {
        console.log('Ejecutando: ' + decisionJson.target);
        exec('start "" "' + decisionJson.target + '"');
        return 'Ejecutando: ' + decisionJson.target;
    }
    else if (decisionJson.action === 'search_google') {
        const query = encodeURIComponent(decisionJson.target);
        exec('start "" "https://www.google.com/search?q=' + query + '"');
        return 'Buscando en Google: ' + decisionJson.target;
    }
    return "Comando desconocido";
}
`;

if (!code.includes('handlePythonRouterDecision')) {
    code = code.replace(/module\.exports = {/g, newCode + '\nmodule.exports = {\n    handlePythonRouterDecision,');
    fs.writeFileSync('jarvis-app/backend/services/systemService.js', code);
    console.log("systemService updated");
} else {
    console.log("Already updated");
}
