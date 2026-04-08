# Jarvis OS - Asistente Virtual Inteligente

Sistema de asistente virtual controlado por voz inspirado en "Jarvis", equipado con integración de Inteligencia Artificial (OpenAI), reconocimiento y síntesis de voz, sistema de modos dinámicos y control del sistema operativo.

## ❤️ Características Principales
- **Reconocimiento de Voz (Web Speech API)**: Escucha pasiva y activación por voz ("Hola Jarvis").
- **Síntesis de Voz (Browser TTS)**: Jarvis habla sus respuestas con voz natural.
- **Sistema Multimodo**: Comportamiento adaptativo según el modo ("Estudio", "Juego", "Productividad", o modos personalizados).
- **Control de la PC**: Abre aplicaciones locales de tu sistema ("Abrir Chrome", "Abrir Calculadora").
- **Interfaz UI Futurista**: Diseño moderno Glassmorphism. Animaciones fluídas con HUD.

## 🛠️ Requisitos Previos
1. **Node.js**: Instalado en tu computadora (v16.0.0 o superior).
2. **Navegador**: Google Chrome o Edge son necesarios (Safari/Firefox tienen soporte limitado para Web Speech API continuo).
3. **OpenAI API Key**: Necesitas una clave API de OpenAI para que el cerebro de Jarvis responda preguntas inteligentemente.

---

## 🚀 Instalación Paso a Paso

### 1. Preparar las dependencias
Abre tu terminal, PowerShell o CMD y navega al directorio del backend:
```bash
cd c:\Users\Rodrigo\Desktop\IA\jarvis-app\backend
```

Ejecuta el siguiente comando para instalar todo lo necesario (express, socket.io, openai, cors, dotenv):
```bash
npm install
```

### 2. Configurar Inteligencia Artificial
En la misma carpeta `backend`, abre el archivo `.env`. Verás algo como:
```env
OPENAI_API_KEY=tu_api_key_aqui
PORT=3000
```
Reemplaza `tu_api_key_aqui` por tu clave secreta obtenida en `platform.openai.com`.

### 3. Ejecutar Sistema Jarvis

En la consola, ejecuta:
```bash
npm start
```

Deberías ver visualmente en consola que el servidor se activó.

### 4. Abrir la Interfaz de Usuario
Jarvis está diseñado para correr tanto en web como de interfaz. Simplemente dirígete a:
**http://localhost:3000** 

Verás la grandiosa interfaz de Jarvis.
Haz click en el botón **INICIAR SISTEMA** inferior. El navegador te solicitará permisos de micrófono: ACÉPTALOS.

---

## 🎤 Cómo hablar con Jarvis

Una vez encendido:
- **Activación por voz:** Di "Hola Jarvis" para llamar su atención, seguido del comando o pregunta.
- **Creación de modos verbal:** Di *"Crear nuevo modo"*, e instantáneamente abrirá el panel mágico.
- **Intercambio verbal de modos:** Di *"Activar modo Juego"* y su cerebro transicionará automáticamente.
- **Control de tu Windows:** Di *"Abrir Chrome"* o *"Abrir Calculadora"* para pedirle a tu Node.js local que ejecute un proceso hijo y abra el software.

Disfruta desarrollando y escalando este increíble asistente interactivo.
