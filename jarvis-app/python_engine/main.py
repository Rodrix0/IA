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

# --- 1. NORMALIZADOR (Arregla "bitcoi", "theter", etc.) ---
def normalizar_consulta(texto: str) -> str:
    t = texto.lower()
    # Mapeo de errores comunes
    reemplazos = {
        "bitcoi": "bitcoin", "theter": "tether", "u$d": "dolar",
        "oficial": "dolar oficial", "tarjeta": "dolar tarjeta",
        "mep": "dolar mep", "solana": "solana crypto"
    }
    for error, correccion in reemplazos.items():
        if error in t: t = t.replace(error, correccion)
    return t

# --- 2. MOTOR FINANCIERO (Dólar y Cripto) ---
def get_financial_data(query: str):
    low = query.lower()
    data_output = "--- DATOS FINANCIEROS REALES 2026 ---\n"
    
    # Dólares Argentina (Plan A)
    try:
        r = requests.get("https://dolarapi.com/v1/dolares", timeout=10)
        if r.status_code == 200:
            for d in r.json():
                data_output += f"Dólar {d['nombre']}: Compra ${d['compra']} | Venta ${d['venta']}\n"
    except: data_output += "Error en DolarAPI.\n"

    # Criptos (Binance)
    symbols = {'bitcoin': 'BTC', 'ethereum': 'ETH', 'solana': 'SOL', 'xrp': 'XRP', 'tron': 'TRX', 'tether': 'USDT', 'usdt': 'USDT'}
    target = None
    for name, sym in symbols.items():
        if name in low: target = sym; break
    
    if target:
        try:
            ticker = f"{target}USDT" if target != "USDT" else "USDTUSDC"
            r_c = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={ticker}", timeout=5)
            if r_c.status_code == 200:
                p = float(r_c.json()['price'])
                data_output += f"CRIPTO: 1 {target} vale {p:,.2f} USD (Dólares)\n"
        except: data_output += f"No pude conectar con Binance para {target}.\n"
    
    return data_output

# --- 3. MOTOR DEPORTIVO (SofaScore + Web Fallback) ---
async def get_sports_info(team_query: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    res_deportiva = ""
    async with httpx.AsyncClient(headers=headers, timeout=10) as client:
        try:
            # Intento SofaScore
            search = await client.get(f"https://api.sofascore.com/api/v1/search/all?q={team_query}&page=0")
            team = next((i for i in search.json().get('results', []) if i.get('type') == 'team'), None)
            if team:
                team_id = team['entity']['id']
                events = await client.get(f"https://api.sofascore.com/api/v1/team/{team_id}/events/next/0")
                next_event = events.json().get('events', [])[:1]
                if next_event:
                    p = next_event[0]
                    fecha = datetime.datetime.fromtimestamp(p['startTimestamp']).strftime('%d/%m/%Y %H:%M')
                    res_deportiva = f"PRÓXIMO PARTIDO: {p['homeTeam']['name']} vs {p['awayTeam']['name']} el {fecha}."
                else:
                    res_deportiva = f"No hay partidos próximos programados para {team['entity']['name']}."
            else:
                # Fallback a Web Search específico para fútbol
                with DDGS() as ddgs:
                    s = list(ddgs.text(f"cuándo juega {team_query} proximo partido 2026", max_results=2))
                    res_deportiva = "\n".join([r['body'] for r in s])
        except: res_deportiva = "Error buscando deportes."
    return res_deportiva

# --- 4. ROUTER DE INTELIGENCIA ---
class UserQuery(BaseModel):
    query: str

@app.post("/api/v1/query")
async def process_query(req: UserQuery):
    original_text = req.query
    user_text = normalizar_consulta(original_text)
    low = user_text.lower()
    ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    contexto = ""
    # Clasificación robusta
    if any(w in low for w in ['dolar', 'blue', 'mep', 'tarjeta', 'oficial', 'bitcoin', 'btc', 'solana', 'xrp', 'crypto', 'tether', 'usdt', 'eth']):
        contexto = get_financial_data(user_text)
    elif any(w in low for w in ['juega', 'partido', 'barcelona', 'boca', 'river', 'madrid', 'futbol']):
        contexto = await get_sports_info(user_text)
    else:
        with DDGS() as ddgs:
            try:
                search = list(ddgs.text(f"{original_text} argentina 2026", max_results=3, timelimit='w'))
                contexto = "\n".join([s.get('body', '') for s in search])
            except: contexto = "Sin resultados web."

    # --- PROMPT DEFINITIVO (BLOQUEO DE "NO TENGO ACCESO") ---
    prompt_synthesis = f"""
    SISTEMA: Eres Jarvis, el asistente de Rodrigo. 
    ESTADO: Año 2026. Localización: Corrientes.
    
    CONTEXTO OBTENIDO (USAR ESTO):
    {contexto}

    PREGUNTA: {original_text}

    REGLAS OBLIGATORIAS:
    1. PROHIBIDO decir "No tengo acceso a tiempo real". Los datos de arriba SON tiempo real.
    2. Si el contexto dice "PRÓXIMO PARTIDO", da la fecha y rival.
    3. Si el contexto tiene precios de cripto (USD) o dólar (ARS), dalos directo.
    4. Responde con estilo Jarvis (Ejecutivo, elegante, canchero).
    5. Si el contexto está vacío o falla, di: "Señor, los servicios externos están caídos, no puedo darle el dato exacto ahora".
    """

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post("http://127.0.0.1:11434/api/generate", 
                json={
                    "model": "llama3.1:latest", 
                    "prompt": prompt_synthesis, 
                    "stream": False,
                    "options": {"temperature": 0} # 0 para que no invente nada
                })
            final_reply = res.json().get("response", "Sistemas fuera de línea, señor.")
            return {"status": "success", "data": {"action": "reply", "message": final_reply}}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
