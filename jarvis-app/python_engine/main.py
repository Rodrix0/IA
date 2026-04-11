from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import datetime
import subprocess

app = FastAPI()

class ActionRequest(BaseModel):
    action: str
    target: str = None
    message: str = None
    parameters: dict = {}

@app.post("/execute")
async def execute_action(req: ActionRequest):
    print(f"Ejecutando acción: {req.action} - Objetivo: {req.target}")
    
    if req.action == "send_whatsapp":
        # Aquí podrías usar pywhatkit, pero si ya tenemos el script de PowerShell que funciona bien:
        if req.target and req.message:
            try:
                # Usar el script de PowerShell existente
                # Asumiendo que se ejecuta desde la raíz del proyecto o ajustando la ruta
                result = subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass", 
                    "-File", "../backend/scripts/sendWhatsAppByName.ps1", 
                    "-ContactName", req.target, 
                    "-MessageText", req.message
                ], capture_output=True, text=True)
                
                return {"status": "success", "message": "Mensaje de WhatsApp enviado a través de PowerShell.", "output": result.stdout}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Faltan parámetros (target o message)"}
        
    elif req.action == "send_email":
        # Implementar envío de correo
        return {"status": "success", "message": f"Simulando envío de correo a {req.target}"}
        
    elif req.action == "search_web":
        # Scraping o búsqueda 
        query = req.parameters.get("query", "")
        return {"status": "success", "message": f"Buscando en web: {query}"}
        
    else:
        return {"status": "error", "message": f"Acción '{req.action}' no reconocida por el motor de Python."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
