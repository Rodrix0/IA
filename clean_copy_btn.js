const fs = require('fs');
let code = fs.readFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/app.js', 'utf8');
code = code.replace(/const btnCopy = document\.getElementById\('btn-copy-doc'\);\n*/g, '');
code = code.replace(/if \(btnCopy\) \{\s*btnCopy\.addEventListener\('click', \(\) => \{\s*const textToCopy = jarvisBox\.innerText;\s*[/ /]*Copia el texto sin las etiquetas html pero con los saltos\s*navigator\.clipboard\.writeText\(textToCopy\)\.then\(\(\) => \{\s*const originalIcon = btnCopy\.innerHTML;\s*btnCopy\.innerHTML = '<i class=\"fa-solid fa-check\"><\/i> Copiado!';\s*setTimeout\(\(\) => btnCopy\.innerHTML = originalIcon, 2500\);\s*\}\);\s*\}\);\s*\}\n*/g, '');
code = code.replace(/const b1 = document\.getElementById\('btn-copy-doc'\); /g, '');
code = code.replace(/if\(b1\) b1\.style\.display = 'none'; /g, '');
fs.writeFileSync('c:/Users/Rodrigo/Desktop/IA/jarvis-app/frontend/app.js', code);
