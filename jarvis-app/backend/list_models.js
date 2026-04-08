require('dotenv').config();

fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${process.env.GEMINI_API_KEY}`)
.then(res => res.json())
.then(data => {
    if(data.models) {
        console.log("Modelos Disponibles en tu Cuenta:");
        data.models.forEach(m => {
            console.log(`- Nombre: ${m.name}`);
            console.log(`  Métodos soportados: ${m.supportedGenerationMethods.join(', ')}`);
        });
    } else {
        console.log("Respuesta de la API:", data);
    }
})
.catch(err => console.error("Error al listar modelos:", err));
