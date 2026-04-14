const fs = require('fs');
let css = fs.readFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', 'utf8');

// The input area has a bottom gap issue
css = css.replace(/\.context-input-container\s*\{[^}]+\}/g, '.context-input-container {\n    width: 100%;\n    max-width: 800px;\n    flex-shrink: 0;\n    display: flex;\n    flex-direction: row;\n    gap: 12px;\n    background: var(--bg-solid-panel);\n    border: 1px solid var(--border-soft);\n    border-radius: 50px;\n    padding: 8px 16px;\n    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);\n    align-items: center;\n    transition: all 0.2s ease;\n    margin: 0 auto 12px auto;\n}');

css = css.replace(/\.controls\s*\{[^}]+\}/g, '.controls {\n    flex-shrink: 0;\n    margin: 0 auto;\n}');

fs.writeFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', css, 'utf8');
