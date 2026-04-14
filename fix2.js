const fs = require('fs');
let css = fs.readFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', 'utf8');

// Fix visualizer heights
css = css.replace(/\.visualizer-container\s*\{[^}]+\}/g, '.visualizer-container {\n    height: 160px;\n    flex-shrink: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    margin: 10px 0 30px 0;\n    position: relative;\n}');

// Fix ring sizes
css = css.replace(/\.ring\s*\{[^}]+\}/g, '.ring {\n    width: 160px;\n    height: 160px;\n    border-radius: 50%;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    position: relative;\n}');

css = css.replace(/\.core\s*\{[^}]+\}/g, '.core {\n    width: 100px;\n    height: 100px;\n    border-radius: 50%;\n    background: var(--bg-solid-panel);\n    border: 1px solid var(--border-soft);\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    font-size: 2.5rem;\n    color: var(--text-secondary);\n    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);\n    z-index: 2;\n}');

// Restore flex: 1 for transcript-box when there is text so it fills the gap and pushes everything to top/bottom cleanly.
// Actually, if we want it centered when empty, but fill space when full:
// We can use flex-grow: 1, max-height: 100%
css = css.replace(/\.transcript-box\s*\{[^}]+\}/g, '.transcript-box {\n    width: 100%;\n    max-width: 800px;\n    background: var(--glass-highlight);\n    border: 1px solid var(--border-soft);\n    border-radius: 16px;\n    padding: 24px;\n    margin-bottom: 20px;\n    display: flex;\n    flex-direction: column;\n    flex: 1 1 auto;\n    width: 100%;\n    max-height: 55vh;\n    overflow: hidden;\n}');

fs.writeFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', css, 'utf8');
