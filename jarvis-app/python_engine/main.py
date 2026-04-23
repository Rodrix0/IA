from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
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
        "model": "llama3.1:latest",
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
3. Añade un docstring a `execute` que diga exactamente qué hace en 1 sola linea corta.
4. NUNCA escribas explicaciones ni texto fuera de los bloques de codigo.
5. Usa código seguro.

Formato esperado:
```python
def execute(**kwargs):
    \"\"\"Descripción corta de lo que hace (max 100 caracteres)\"\"\"
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

import re
import datetime
import unicodedata
from duckduckgo_search import DDGS

# --- 1. MOTOR DE DATOS TOTAL (Dólar + Cripto en un solo bloque) ---
def get_financial_snapshot():
    """Trae toda la artillería financiera de una sola vez para que la IA no alucine"""
    snapshot = "--- DATOS FINANCIEROS ARGENTINA (2026) ---\n"
    
    # Dólares (DolarAPI)
    try:
        r = requests.get("https://dolarapi.com/v1/dolares", timeout=8)
        if r.status_code == 200:
            for d in r.json():
                snapshot += f"- Dólar {d['nombre']}: Compra ${d['compra']} | Venta ${d['venta']}\n"
    except: snapshot += "Error cargando Dólares.\n"

    # Criptos Principales (Binance)
    snapshot += "\n--- MERCADO CRIPTO GLOBAL (USD) ---\n"
    coins = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT', 'XRP': 'XRPUSDT', 'USDT': 'USDTUSDC', 'TRX': 'TRXUSDT'}
    for name, ticker in coins.items():
        try:
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={ticker}", timeout=5)
            if res.status_code == 200:
                p = float(res.json()['price'])
                snapshot += f"- {name}: {p:,.2f} USD\n"
        except: continue
        
    return snapshot

# --- 2. MOTOR DEPORTIVO (SofaScore + Fallback) ---
async def get_sports_info(query: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, timeout=10) as client:
        try:
            search = await client.get(f"https://api.sofascore.com/api/v1/search/all?q={query}&page=0")
            team = next((i for i in search.json().get('results', []) if i.get('type') == 'team'), None)
            if team:
                t_id = team['entity']['id']
                events = await client.get(f"https://api.sofascore.com/api/v1/team/{t_id}/events/next/0")
                nxt = events.json().get('events', [])[:1]
                if nxt:
                    p = nxt[0]
                    fecha = datetime.datetime.fromtimestamp(p['startTimestamp']).strftime('%d/%m/%Y %H:%M')
                    return f"PRÓXIMO PARTIDO DE {team['entity']['name']}: {p['homeTeam']['name']} vs {p['awayTeam']['name']} el {fecha} (Hora Local)."
            
            # Si no hay SofaScore, buscador web
            with DDGS() as ddgs:
                s = list(ddgs.text(f"cuándo juega {query} 2026 proximo partido", max_results=2))
                return "\n".join([r['body'] for r in s])
        except: return "No tengo datos deportivos ahora, señor."

# --- 3. ROUTER DE INTELIGENCIA ---
class UserQuery(BaseModel):
    query: str

@app.post("/api/v1/query")
async def process_query(req: UserQuery):
    u_text = req.query.lower()
    ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    contexto = ""
    # Clasificación mejorada
    es_dinero = any(w in u_text for w in ['dolar', 'blue', 'mep', 'tarjeta', 'oficial', 'bitcoin', 'btc', 'solana', 'xrp', 'tether', 'usdt', 'eth', 'tron', 'trx'])
    es_futbol = any(w in u_text for w in ['juega', 'partido', 'barcelona', 'boca', 'river', 'madrid', 'equipo'])

    if es_dinero:
        contexto = get_financial_snapshot()
    elif es_futbol:
        contexto = await get_sports_info(u_text)
    else:
        with DDGS() as ddgs:
            try:
                res = list(ddgs.text(f"{req.query} argentina 2026", max_results=3, timelimit='w'))
                contexto = "\n".join([r['body'] for r in res])
            except: contexto = "Sin conexión web."

    # --- EL PROMPT DE HIERRO ---
    prompt_synthesis = f"""
    SISTEMA: Eres Jarvis, el asistente personal de Rodrigo. 
    AÑO ACTUAL: 2026. LOCALIZACIÓN: Corrientes, Argentina.
    
    DATOS REALES DEL SISTEMA (USAR ESTO O NADA):
    {contexto}

    PREGUNTA DEL JEFE: {req.query}

    INSTRUCCIONES CRÍTICAS:
    1. PROHIBIDO decir "No tengo acceso". Los datos de arriba SON tu acceso.
    2. Si el contexto tiene una lista de dólares, busca el que te pidió Rodrigo (Blue, Oficial, Tarjeta, etc) y da el precio de venta.
    3. Si el contexto tiene criptos, dalas en USD.
    4. Si no hay datos financieros en el contexto, di: "Señor, los mercados están cerrados o fuera de línea".
    5. No des consejos, sé directo y elegante.
    """

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post("http://127.0.0.1:11434/api/generate", 
                json={
                    "model": "llama3.1:latest", 
                    "prompt": prompt_synthesis, 
                    "stream": False,
                    "options": {"temperature": 0} # 0 = CERO alucinación
                })
            return {"status": "success", "data": {"action": "reply", "message": res.json().get("response")}}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
