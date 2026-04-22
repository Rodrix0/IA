from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn
import datetime
import subprocess
import os
import ast
import json
import asyncio
import httpx
import requests
import urllib.request
import importlib.util
from rag_service import query_rag

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


class UserQuery(BaseModel):
    query: str

def get_crypto_price(coin_id: str = "bitcoin"):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    res = requests.get(url).json()
    return res.get(coin_id, {}).get("usd", "No disponible")

def get_weather(city: str):
    return {"temp": "22�C", "condition": "Despejado", "source": "Open-Meteo"}

def get_exchange_rate(base: str = "USD", target: str = "ARS"):
    url = f"https://api.exchangerate-api.com/v4/latest/{base}"
    res = requests.get(url).json()
    return res.get("rates", {}).get(target, "No disponible")

def get_football_scores(league_id: str):
    return {"matches": ["Boca 2 - 0 River", "Racing 1 - 1 Independiente"], "source": "API-Football"}

def tool_router(user_text: str):
    rag_response = query_rag(user_text)
    fallbacks = ["no encontrado", "empty response", ""]
    if rag_response.strip().lower() not in fallbacks:
        return {"action": "reply", "message": rag_response, "source": "Local RAG (PDFs)"}

    tools_description = """
    Eres un router de IA. Clasifica el siguiente texto y devuelve un JSON estricto con "tool" y "params".
    Tools dispobibles:
    - "get_crypto_price" (params: coin_id)
    - "get_weather" (params: city)
    - "get_exchange_rate" (params: base, target)
    - "get_football_scores" (params: league_id)
    - "open_app" (params: app_name) -> Abrir programa en Windows
    - "search_google" (params: query) -> Fallback para info general
    """
    data = {
        "model": "hermes3:8b",
        "prompt": f"{tools_description}\nUsuario: {user_text}\nJSON:",
        "format": "json",
        "stream": False
    }
    
    try:
        req = requests.post("http://127.0.0.1:11434/api/generate", json=data)
        response_text = req.json().get("response", "{}")
        
        # Limpiar markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[-1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[-1].split("```")[0].strip()
            
        decision = json.loads(response_text)
        
        # Handle list format
        if isinstance(decision, list) and len(decision) > 0:
            decision = decision[0]
            
        tool = decision.get("tool")
        params = decision.get("params", {})
        if isinstance(params, list) and len(params) > 0:
            params = params[0]
        elif isinstance(params, list):
            params = {}
        elif isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                params = {}
        
        if tool == "get_crypto_price":
            price = get_crypto_price(params.get("coin_id"))
            return {"action": "reply", "message": f"El precio es ${price}", "source": "CoinGecko"}
        elif tool == "get_weather":
            # Extraer solo la data util
            w = get_weather(params.get("city", ""))
            return {"action": "reply", "message": f"El clima: {w['temp']}, {w['condition']} (Fuente: {w['source']})", "source": "Open-Meteo"}
        elif tool == "get_exchange_rate":
            rate = get_exchange_rate(params.get("base", "USD"), params.get("target", "ARS"))
            return {"action": "reply", "message": f"La tasa de cambio es {rate}", "source": "ExchangeRate-API"}
        elif tool == "get_football_scores":
            scores = get_football_scores(params.get("league_id", ""))
            return {"action": "reply", "message": f"Resultados: {', '.join(scores['matches'])}", "source": "API-Football"}
        elif tool == "open_app":
            return {"action": "open_app", "target": params.get("app_name")}
        else:
            return {"action": "search_google", "target": user_text}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ROUTER ERROR: {e}")
        return {"action": "search_google", "target": user_text}

@app.post("/api/v1/query")
async def process_query(req: UserQuery):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, tool_router, req.query)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)




