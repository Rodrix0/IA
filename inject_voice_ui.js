const fs = require('fs');
const filePath = 'c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/index.html';
let html = fs.readFileSync(filePath, 'utf8');

const targetStr = '<div class="system-status">';
const injectStr = \
            <div class="system-status" style="margin-right: 15px;">
                <select id="voice-select" style="background: transparent; color: var(--accent); border: 1px solid var(--accent); border-radius: 4px; padding: 2px; font-family: 'Rajdhani'; outline: none; cursor: pointer; max-width: 150px; text-overflow: ellipsis;">
                    <option value="">Cargando voces...</option>
                </select>
            </div>
            \;

if (html.includes(targetStr) && !html.includes('id="voice-select"')) {
    html = html.replace('<div class="system-status">', injectStr + '<div class="system-status">');
    fs.writeFileSync(filePath, html, 'utf8');
    console.log('Voice selector injected into index.html');
} else {
    console.log('Selector already exists or target not found');
}
