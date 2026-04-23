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

import re
import datetime
import unicodedata
from ddgs import DDGS

# --- 1. EL LIMPIADOR DE BASURA (Evita que Hermes se maree) ---
def limpiar_texto(texto: str, max_chars: int = 1200) -> str:
    if not texto: return ""
    texto = re.sub(r'<[^>]+>', '', texto) # Quitar HTML
    texto = unicodedata.normalize('NFKC', texto) # Normalizar acentos y símbolos
    texto = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', texto) # Quitar caracteres de control
    texto = re.sub(r'http[s]?://\S+', '', texto) # Quitar URLs que ensucian
    texto = re.sub(r'\s+', ' ', texto).strip() # Colapsar espacios múltiples
    return texto[:max_chars]

# --- 2. EL BUSCADOR "SUPER SEARCH" (Con el filtro 'w' que descubriste) ---
def super_search(query: str):
    print(f"[Jarvis Search] 🌐 Investigando en tiempo real: {query}")
    try:
        # Usamos 'w' para asegurar resultados frescos pero no vacíos
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(f"{query}", max_results=5, timelimit='w'))
           
        if not raw_results:
            return "No se encontró información reciente en internet."

        limpios = []
        for r in raw_results:
            titulo = limpiar_texto(r.get('title', ''))
            cuerpo = limpiar_texto(r.get('body', ''))
            limpios.append(f"FUENTE: {titulo} | INFO: {cuerpo}")

        return "\n".join(limpios)
    except Exception as e:
        print(f"Error en DDGS: {e}")
        return "Error de conexión con los servicios de búsqueda."

# --- AGENTE DE DEPORTES SOFASCORE ---
async def get_sofascore_info(team_query: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=10) as client:
        # PASO 1: Buscar el equipo para obtener su ID
        search_url = f"https://api.sofascore.com/api/v1/search/all?q={team_query}&page=0"
        search_res = await client.get(search_url)
        
        if search_res.status_code != 200:
            return "No pude conectar con el servidor de SofaScore."
            
        search_data = search_res.json()
        
        # Filtramos para encontrar el primer resultado que sea un "team"
        team = next((item for item in search_data.get('results', []) if item.get('type') == 'team'), None)
        
        if not team:
            return f"No encontré al equipo '{team_query}' en SofaScore."
            
        team_id = team['entity']['id']
        team_name = team['entity']['name']
        
        # PASO 2: Traer los últimos y próximos partidos usando el ID
        events_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0" # 'last' para resultados, 'next' para próximos
        events_res = await client.get(events_url)
        
        if events_res.status_code != 200:
            return f"Encontré a {team_name}, pero no pude traer sus partidos."
            
        events_data = events_res.json()
        partidos = events_data.get('events', [])[:3] # Traemos los últimos 3
        
        resumen = f"Datos de SofaScore para {team_name}:\n"
        for p in partidos:
            home = p['homeTeam']['shortName']
            away = p['awayTeam']['shortName']
            home_score = p['homeScore'].get('current', 0)
            away_score = p['awayScore'].get('current', 0)
            status = p['status']['description']
            resumen += f"- {home} {home_score} vs {away_score} {away} ({status})\n"
            
        return resumen

# --- 3. EL ROUTER DE INTELIGENCIA ---
class UserQuery(BaseModel):
    query: str

@app.post("/api/v1/query")
async def process_query(req: UserQuery):
    user_text = req.query
    
    # --- FECHA DINÁMICA AUTOMÁTICA ---
    ahora = datetime.datetime.now()
    fecha_hoy = ahora.strftime("%d/%m/%Y")
    anio_actual = ahora.strftime("%Y")
    dia_semana = ahora.strftime("%A") # Ej: Wednesday

    # --- OPTIMIZACIÓN DE QUERIES SEGÚN INTENTO ---
    search_query = user_text
    lower_text = user_text.lower()
    
    if any(w in lower_text for w in ['barcelona', 'boca', 'partido', 'sofascore']):
        raw_info = await get_sofascore_info(user_text) 
        if "No pude conectar" in raw_info or "No encontré" in raw_info or "no pude traer" in raw_info:
            print("[Jarvis] SofaScore sin datos o bloqueado. Usando Super Search de respaldo...")
            search_query = f"resultado o próximo partido de {user_text} fecha horario oficial hoy"
            raw_info = super_search(search_query)
    else:
        # Fallback a tu búsqueda normal de internet
        if any(w in lower_text for w in ['dolar', 'blue', 'mep', 'cotizacion']):
            search_query = f"cotizacion dolar blue oficial mep argentina hoy cronista ambito financiero"
        elif any(w in lower_text for w in ['clima', 'tiempo', 'temperatura']):
            search_query = f"clima actual en Corrientes Argentina pronóstico hoy {fecha_hoy}"
        elif any(w in lower_text for w in ['bitcoin', 'btc', 'cripto']):
            search_query = f"precio bitcoin hoy usd en vivo binance coinmarketcap"

        raw_info = super_search(search_query)

    # --- PROMPT MAESTRO (Instrucciones para que Hermes no alucine) ---
    prompt_synthesis = f"""
    SISTEMA: Eres Jarvis, el asistente personal de Rodrigo.
    FECHA ACTUAL DEL SISTEMA: {dia_semana}, {fecha_hoy}.
    LOCALIZACIÓN: Corrientes, Argentina.

    DATOS OBTENIDOS DE INTERNET (ÚLTIMA SEMANA):
    {raw_info}

    PREGUNTA DEL USUARIO: {user_text}

    REGLAS DE RESPUESTA CRÍTICAS:
    1. Usa EXCLUSIVAMENTE los datos de internet proporcionados arriba.
    2. Si los datos mencionan fechas como '2022' o '2023', IGNÓRALOS por completo.
    3. Si internet dice que el dólar está a menos de $900, es información vieja; no la digas.
    4. Responde de forma directa y "canchera" (argentino elegante). No digas "según los datos...", simplemente da la info.
    5. Si no hay datos claros para hoy, di: "Señor, no logré obtener reportes confiables de esta semana para esa consulta".
    6. PROHIBIDO INVENTAR: Si en los datos dice que hubo un error o que no se encontró información, di que no tienes los datos y NO inventes resultados falsos.
    """

    try:
        # Llamada a Ollama
        res = requests.post("http://127.0.0.1:11434/api/generate", 
                            json={"model": "hermes3:8b", "prompt": prompt_synthesis, "stream": False}, 
                            timeout=25).json()
        
        final_reply = res.get("response", "Señor, mis sistemas de síntesis fallaron.")
        return {"status": "success", "data": {"action": "reply", "message": final_reply}}
    
    except Exception as e:
        return {"status": "error", "message": f"Fallo en Ollama: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
