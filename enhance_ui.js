const fs = require('fs');
const file = 'c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/index.html';
let html = fs.readFileSync(file, 'utf8');

const targetHeader = '</head>';
const injectionHeader = \
    <!-- Markdown and Syntax Highlighting -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
    
    <!-- MathJax for Formulas -->
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    
    <!-- Custom styling for markdown elements in Jarvis UI -->
    <style>
        .jarvis-text { text-align: left; display: block; overflow-y: auto; max-height: 45vh; padding: 15px; font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; line-height: 1.6; }
        .jarvis-text h1, .jarvis-text h2, .jarvis-text h3 { color: var(--primary-cyan); margin-top: 15px; border-bottom: 1px solid rgba(0, 242, 254, 0.2); padding-bottom: 5px; }
        .jarvis-text p { margin-bottom: 15px; }
        .jarvis-text ul, .jarvis-text ol { margin-left: 20px; margin-bottom: 15px; }
        .jarvis-text li { margin-bottom: 5px; }
        .jarvis-text code { background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 4px; color: #ff00ff; font-family: monospace; }
        .jarvis-text pre code { background: transparent; padding: 0; color: inherit; }
        .jarvis-text pre { background: rgba(0,0,0,0.8); border: 1px solid var(--accent); padding: 10px; border-radius: 8px; overflow-x: auto; margin-bottom: 15px; }
        
        .action-tool-bar { display: flex; gap: 10px; margin-top: 10px; justify-content: flex-end; }
        .hud-btn { background: rgba(0, 0, 0, 0.5); border: 1px solid var(--accent); color: var(--accent); padding: 5px 15px; cursor: pointer; font-family: 'Orbitron'; font-size: 0.8rem; border-radius: 4px; transition: 0.3s; }
        .hud-btn:hover { background: var(--accent); color: #000; box-shadow: 0 0 10px var(--accent); }
    </style>
</head>\;
html = html.replace('</head>', injectionHeader);

const targetContainer = '<div class="transcript-box">';
const injectionContainer = \
                <div class="transcript-box" style="display:flex; flex-direction:column; max-height: 55vh; margin-bottom: 10px;">
                    <div id="user-transcript" class="user-text" style="flex-shrink: 0;">Esperando interacciÃ³n...</div>
                    <div style="flex-grow: 1; overflow: hidden; display: flex; flex-direction: column;">
                        <div id="jarvis-response" class="jarvis-text">Sistema Jarvis. Inicia el sistema para interactuar.</div>
                    </div>
                    <div class="action-tool-bar">
                        <button id="btn-copy-doc" class="hud-btn" style="display:none;"><i class="fa-regular fa-copy"></i> Copiar Documento</button>
                        <button id="btn-stop-audio" class="hud-btn" style="display:none; color: #ff3366; border-color: #ff3366;"><i class="fa-solid fa-volume-xmark"></i> Silenciar Jarvis</button>
                    </div>
                </div>\;

// Find and replace the transcript box safely
const scriptStart = html.indexOf('<div class="transcript-box">');
if(scriptStart !== -1) {
    const nextNode = html.indexOf('<!-- PANEL DE ARCHIVOS Y LINKS (NUEVO) -->', scriptStart);
    if(nextNode !== -1){
        html = html.substring(0, scriptStart) + injectionContainer + html.substring(nextNode);
    }
}

fs.writeFileSync(file, html, 'utf8');
console.log('UI index updated.');
