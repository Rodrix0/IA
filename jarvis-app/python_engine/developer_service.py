import os, json, subprocess, httpx

# Carpeta de trabajo en tu escritorio
WORKSPACE = os.path.join(os.path.expanduser("~"), "Desktop", "Jarvis_Projects")
if not os.path.exists(WORKSPACE): os.makedirs(WORKSPACE)

class JarvisDeveloper:
    def __init__(self):
        self.active_project = None

    async def execute_full_project(self, big_prompt: str):
        print("[Jarvis Architect] 🏗️ Analizando arquitectura de BrewHub...")
        
        # System Prompt para que Llama genere toda la estructura de una
        system_instructions = """
        Eres un Senior Fullstack Developer. Tu salida DEBE ser un JSON puro.
        Vas a crear la estructura inicial de un proyecto profesional.
        
        ESTRUCTURA OBLIGATORIA:
        {
            "project_name": "BrewHub_App",
            "files": [
                {"name": "index.html", "content": "..."},
                {"name": "style.css", "content": "..."},
                {"name": "server.js", "content": "..."},
                {"name": "README.md", "content": "Instrucciones del proyecto BrewHub"}
            ]
        }
        """

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                res = await client.post("http://127.0.0.1:11434/api/generate", 
                    json={
                        "model": "llama3.1:latest", 
                        "prompt": f"{system_instructions}\n\nPROMPT DEL JEFE:\n{big_prompt}",
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1}
                    })
                
                data = json.loads(res.json().get("response", "{}"))
                return self._deploy_to_windows(data)
        except Exception as e:
            return f"Error en el despliegue: {str(e)}"

    def _deploy_to_windows(self, data):
        p_name = data.get("project_name", "BrewHub")
        p_path = os.path.join(WORKSPACE, p_name)
        if not os.path.exists(p_path): os.makedirs(p_path)

        for f in data.get("files", []):
            with open(os.path.join(p_path, f['name']), "w", encoding="utf-8") as file:
                file.write(f['content'])
        
        # Forzamos la apertura de Visual Studio Code en el directorio del proyecto
        # El comando 'code' es el alias oficial de VS Code en Windows.
        try:
            subprocess.Popen(f'code "{p_path}"', shell=True)
            return f"Señor, el entorno BrewHub está listo. He abierto OpenCode (Visual Studio) en la carpeta del proyecto."
        except Exception as e:
            return f"Proyecto creado, pero no pude lanzar Visual Studio. Error: {str(e)}"

dev_jarvis = JarvisDeveloper()
