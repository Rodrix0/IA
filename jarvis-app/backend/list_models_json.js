const fs = require('fs');
require('dotenv').config();
fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${process.env.GEMINI_API_KEY}`)
.then(res => res.json())
.then(data => {
    fs.writeFileSync('models.json', JSON.stringify(data, null, 2), 'utf8');
})
.catch(err => console.error(err));
