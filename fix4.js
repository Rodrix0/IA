const fs = require('fs');
let css = fs.readFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', 'utf8');

css = css.replace('.center-panel {\n    flex: 1;\n    display: flex;\n    flex-direction: column;\n    align-items: center;\n    justify-content: space-between;\n    padding: 30px 40px 20px 40px;\n    position: relative;\n    overflow: hidden;\n}', '.center-panel {\n    flex: 1;\n    display: flex;\n    flex-direction: column;\n    align-items: center;\n    justify-content: center;\n    padding: 40px;\n    position: relative;\n    overflow: hidden;\n}');

css = css.replace('.visualizer-container {\n    height: 180px;\n    flex-shrink: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    margin: 0 auto;\n    position: relative;\n}', '.visualizer-container {\n    height: 160px;\n    flex-shrink: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    margin: 0 auto 30px auto;\n    position: relative;\n}');

css = css.replace('.transcript-box {\n    width: 100%;\n    max-width: 800px;\n    background: var(--glass-highlight);\n    border: 1px solid var(--border-soft);\n    border-radius: 16px;\n    padding: 24px;\n    margin-bottom: 20px;\n    display: flex;\n    flex-direction: column;\n    flex: 1 1 auto;\n    width: 100%;\n    max-height: 55vh;\n    overflow: hidden;\n}', '.transcript-box {\n    width: 100%;\n    max-width: 800px;\n    background: var(--glass-highlight);\n    border: 1px solid var(--border-soft);\n    border-radius: 16px;\n    padding: 30px;\n    margin: 0 auto 30px auto;\n    display: flex;\n    flex-direction: column;\n    flex: 0 1 auto;\n    min-height: 80px;\n    max-height: calc(100vh - 400px);\n    overflow: hidden;\n}');

fs.writeFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', css, 'utf8');
