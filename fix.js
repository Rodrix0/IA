const fs = require('fs');
let css = fs.readFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', 'utf8');

// Fix .center-panel centering
css = css.replace(/justify-content: flex-start;/g, 'justify-content: center;');

// Fix .transcript-box flex rules to prevent infinite stretch and allow centering
css = css.replace(/\.transcript-box\s*\{[^}]+\}/g, (match) => {
    let replaced = match;
    // Replace flex: 1; with flex: 0 1 auto;
    replaced = replaced.replace(/flex:\s*1;/g, 'flex: 0 1 auto;');
    // Add max-height if not present
    if (!replaced.includes('max-height: 100%;')) {
        replaced = replaced.replace('min-height: 0;', 'min-height: 0;\n    max-height: 100%;');
    }
    return replaced;
});

// Write it back
fs.writeFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/style.css', css, 'utf8');
