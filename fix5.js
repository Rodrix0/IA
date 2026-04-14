const fs = require('fs');
let css = fs.readFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', 'utf8');

css = css.replace('.center-panel {\n    flex: 1;\n    display: flex;\n    flex-direction: column;\n    align-items: center;\n    justify-content: center;\n    padding: 40px;\n    position: relative;\n    overflow: hidden;\n}', '.center-panel {\n    flex: 1;\n    display: flex;\n    flex-direction: column;\n    align-items: center;\n    justify-content: space-between;\n    padding: 40px;\n    position: relative;\n    overflow: hidden;\n}');

css = css.replace('.visualizer-container {\n    height: 160px;\n    flex-shrink: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    margin: 0 auto 30px auto;\n    position: relative;\n}', '.visualizer-container {\n    height: 160px;\n    flex-shrink: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    margin: 10vh auto 30px auto;\n    position: relative;\n}');

fs.writeFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', css, 'utf8');
