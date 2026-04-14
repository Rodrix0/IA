const fs = require('fs');
const file = 'c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/app.js';
let code = fs.readFileSync(file, 'utf8');

// Find the first occurrence of btnCopy
const bIdx = code.indexOf('const btnCopy = document.getElementById(\\\'btn-copy-doc\\\');');
if(bIdx !== -1) {
    const endBIdx = code.lastIndexOf('}');
    // Since it's at the end, just slice at the FIRST occurrence and keep it
    // Wait, let's just regex out the duplicate blocks entirely, then cleanly add one.
    // The easiest is just slicing the file from the start to the first occurrence
    code = code.substring(0, bIdx);
    fs.writeFileSync(file, code, 'utf8');
}
