from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import datetime
import subprocess
import os
import ast
import json
import asyncio
import httpx
import importlib.util

app = FastAPI()

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")
if not os.path.exists(SKILLS_DIR):
    os.makedirs(SKILLS_DIR)

class ActionRequest(BaseModel):
    action: str
    target: str = None
    message: str = None
    parameters: dict = {}

class DevelopRequest(BaseModel):
    objective: str

class ExecuteSkillRequest(BaseModel):
    skill_name: str
    kwargs: dict = {}

async def call_ollama(prompt: str) -> str:
    url = "http://127.0.0.1:11434/api/generate"
    data = {
        "model": "hermes3",
        "prompt": prompt,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return ""

async def generate_and_test_skill(objective: str):
    print(f"[Code-Act] Desarrollando nueva habilidad en las sombras: {objective}")
    
    prompt = f"""Escribe un script de Python puro que cumpla estrictamente este objetivo: "{objective}".
REGLAS:
1. El script DEBE tener una funcion llamada exactamente `execute(**kwargs)` que reciba argumentos (si aplican) y devuelva un string legible explicandolo.
2. NO uses dependencias externas raras que requieran `pip install`. Usa nativas: os, sys, datetime, urllib, json, subprocess, math, random.
3. A�ade un docstring a `execute` que diga exactamente qu� hace en 1 sola linea corta.
4. NUNCA escribas explicaciones ni texto fuera de los bloques de codigo.
5. Usa c�digo seguro.

Formato esperado:
```python
def execute(**kwargs):
    \""\"Descripci�n corta de lo que hace (max 100 caracteres)\"\"\"
    # logica
    return "Resultado final"
```
"""
    
    code_response = await call_ollama(prompt)
    if not code_response:
        print("[Code-Act] ❌ Fallo al comunicarse con Ollama.")
        return
        
    code = ""
    if "```python" in code_response:
        code = code_response.split("```python")[1].split("```")[0].strip()
    elif "```" in code_response:
        code = code_response.split("```")[1].split("```")[0].strip()
    else:
        code = code_response.strip()

    if "def execute(" not in code:
        print("[Code-Act] ❌ El código generado no contiene def execute()")
        return

    name_prompt = f"Dado este objetivo: '{objective}', devuelve SOLAMENTE un nombre de archivo en snake_case corto (sin python ni extensiones). Ej: 'descargar_video'"
    name = await call_ollama(name_prompt).strip().replace(" ", "_").replace("'", "").replace('"', '').replace('.', '').replace(',', '').replace('`', '').lower()
    if not name or len(name) > 30:
        import time
        name = f"custom_{int(time.time())}"
        
    filename = f"skill_{name}.py"
    filepath = os.path.join(SKILLS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    print(f"[Code-Act] ✅ Código guardado en {filename}. Probando sintaxis...")
    
    try:
        ast.parse(code)
        spec = importlib.util.spec_from_file_location(f"skill_{name}", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'execute'):
            print(f"[Code-Act] 🚀 Habilidad {filename} creada y validada sintácticamente con éxito.")
            try:
                alert_text = f"Señor, acabo de terminar de asimilar la nueva habilidad. Ya puede utilizarla cuando desee."
                req = urllib.request.Request("http://127.0.0.1:3000/api/speak", data=json.dumps({"text": alert_text}).encode('utf-8'), headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req)
            except Exception as e:
                pass
        else:
            print(f"[Code-Act] ❌ No se encontró 'execute' en {filename}.")
    except Exception as e:
        print(f"[Code-Act] ❌ Error de sintaxis en {filename}: {e}")
        os.remove(filepath)

@app.post("/develop_skill")
def develop_skill(req: DevelopRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_and_test_skill, req.objective)
    return {"status": "success", "message": f"Estoy diseñando la habilidad '{req.objective}' en mis subprocesos. Te avisaré si logro compilarla."}

@app.get("/list_skills")
def list_skills():
    skills = []
    if not os.path.exists(SKILLS_DIR):
        return skills
        
    for f in os.listdir(SKILLS_DIR):
        if f.startswith("skill_") and f.endswith(".py"):
            skill_name = f[:-3]
            filepath = os.path.join(SKILLS_DIR, f)
            desc = f"SCRIPT EJECUTABLE. Tarea: {skill_name.replace('skill_', '').replace('_', ' ')}. ÚSALA SOLO SI EL USUARIO LA PIDE."
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    source = file.read()
                    parsed = ast.parse(source)
                    for node in parsed.body:
                        if isinstance(node, ast.FunctionDef) and node.name == 'execute':
                            doc = ast.get_docstring(node)
                            if doc:
                                desc = f"SCRIPT PROGRAMADO. {doc.strip().split('\\n')[0]}. Úsalo EXCLUSIVAMENTE si el usuario quiere ejecutar esta herramienta específica de nuevo."
            except:
                pass
                
            skills.append({
                "name": skill_name,
                "description": desc,
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "kwargs_str": {
                            "type": "string",
                            "description": "Cualquier texto o parámetros extra que la habilidad pueda necesitar (opcional)"
                        }
                    }
                }
            })
            
    return skills

@app.post("/execute_skill")
def exec_skill(req: ExecuteSkillRequest):
    filepath = os.path.join(SKILLS_DIR, f"{req.skill_name}.py")
    if not os.path.exists(filepath):
        return {"status": "error", "message": f"No se encontró {req.skill_name}"}
        
    try:
        spec = importlib.util.spec_from_file_location(req.skill_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'execute'):
            result = module.execute(**req.kwargs)
            return {"status": "success", "result": str(result)}
        else:
            return {"status": "error", "message": "Script mal defindo"}
    except Exception as e:
        return {"status": "error", "message": f"Excepción en ejecución: {e}"}

@app.post("/execute")
def execute_action(req: ActionRequest):
    print(f"Ejecutando acción nativa: {req.action}")
    if req.action == "send_whatsapp":
        if req.target and req.message:
            try:
                result = subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass", 
                    "-File", "../backend/scripts/sendWhatsAppByName.ps1", 
                    "-ContactName", req.target, 
                    "-MessageText", req.message
                ], capture_output=True, text=True)
                return {"status": "success", "message": "Mensaje enviado", "output": result.stdout}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Faltan parámetros"}
    elif req.action == "send_email":
        return {"status": "success", "message": f"Correo a {req.target}"}
    elif req.action == "search_web":
        return {"status": "success", "message": "Buscando web"}
    else:
        return {"status": "error", "message": "Acción no reconocida"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)




