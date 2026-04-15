import sys
import json
import os
import cv2
import customtkinter as ctk
import time
import ctypes
from PIL import Image, ImageTk

# Directorios de la app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'backend', 'data')
SECURITY_FILE = os.path.join(DATA_DIR, 'security.json')
MODEL_FILE = os.path.join(DATA_DIR, 'trainer.yml')
STATE_FILE = os.path.join(DATA_DIR, 'lock_state.txt')

class JarvisLockScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Arreglar problema de Windows donde "se queda a la mitad" (DPI Awareness)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.title("JARVIS - Securing Perimeter")
        
        # Cobertura extrema para TODOS los monitores y resoluciones sin bordes
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(78) # SM_CXVIRTUALSCREEN (ancho total de todos los monitores unidos)
        h = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN (alto total)
        x = user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN (origen X)
        y = user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN (origen Y)

        # Si por alguna razón VirtualScreen devuelve 0, usamos medidas locales
        if w == 0 or h == 0:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            x, y = 0, 0

        self.geometry(f"{w}x{h}+{x}+{y}")
        self.overrideredirect(True) # Quita absolutamente todo el marco del SO
        self.attributes('-topmost', True)
        self.config(cursor="none") # Ocultamos el mouse para sentirlo nativo

        # Configurar colores y grid principal
        self.configure(fg_color="#030303")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Contenedor central
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=0)
        
        # Logo o texto de JARVIS
        self.header = ctk.CTkLabel(self.center_frame, text="SISTEMA BLOQUEADO", font=("Inter", 30, "bold"), text_color="#ff1a1a")
        self.header.pack(pady=(0, 10))

        self.info_label = ctk.CTkLabel(self.center_frame, text="ESPERANDO RECONOCIMIENTO BIOMÉTRICO...", font=("Inter", 16), text_color="#00ffcc")
        self.info_label.pack(pady=(0, 30))
        
        # Visor de la cámara (intentaremos darle un look de escaner)
        self.video_label = ctk.CTkLabel(self.center_frame, text="")
        self.video_label.pack(pady=10)
        
        # Teclado (Oculto al estilo "Teclea tu pin a ciegas o presiona en el centro")
        self.pin_var = ctk.StringVar()
        self.pin_entry = ctk.CTkEntry(self.center_frame, textvariable=self.pin_var, width=150, justify="center", show="•", font=("Inter", 20), fg_color="#111", border_color="#333")
        self.pin_entry.pack(pady=(30, 5))
        self.pin_entry.bind("<Return>", self.verify_pin)
        self.pin_entry.focus() # Enfocar para recibir pines ocultos
        
        self.hint = ctk.CTkLabel(self.center_frame, text="Usa el teclado numérico para PIN manual", font=("Inter", 11), text_color="#444")
        self.hint.pack()

        # Datos de Seguridad
        self.security_data = self.load_security_data()
        
        # Sistema de Biometria
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.model_loaded = False
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            if os.path.exists(MODEL_FILE):
                self.recognizer.read(MODEL_FILE)
                self.model_loaded = True
            else:
                self.info_label.configure(text="SISTEMA SIN ENTRENAR (BIOMETRÍA DESACTIVADA)", text_color="orange")
        except Exception as e:
            print("Error cargando LBPH:", e)

        # En vez de arrancar la camara y la UI de golpe, nos ocultamos
        # y escuchamos permanentemente el archivo de estado
        self.unlocked = False
        self.is_active = False
        self.withdraw() # Oculto en RAM
        
        self.check_state_loop()

    def check_state_loop(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = f.read().strip()
                
                if state == "SHOW" and not self.is_active:
                    self.activate_lockscreen()
        except:
            pass
        self.after(200, self.check_state_loop) # Revisar cada 200ms

    def activate_lockscreen(self):
        self.is_active = True
        self.unlocked = False
        self.info_label.configure(text="ESPERANDO RECONOCIMIENTO BIOMÉTRICO...", text_color="#00ffcc")
        self.header.configure(text="SISTEMA BLOQUEADO", text_color="#ff1a1a")

        # 1. MOSTRAR LA PANTALLA NEGRA INSTANTÁNEAMENTE (0ms)
        self.deiconify() 
        self.attributes('-topmost', True)
        self.pin_entry.focus()
        self.update() # Forzar a Windows a dibujar la ventana antes del bloqueo de la cámara

        # 2. Iniciar cámara fresca (Este proceso tarda ~1.5 seg a nivel de Hardware/USB)
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.update_camera()

    def load_security_data(self):
        if os.path.exists(SECURITY_FILE):
            with open(SECURITY_FILE, 'r') as f:
                return json.load(f)
        return {"pin": "0000"}

    def verify_pin(self, event=None):
        entered_pin = self.pin_var.get()
        if entered_pin == self.security_data.get("pin"):
            self.unlock_system()
        else:
            self.info_label.configure(text="ACCESO DENEGADO", text_color="#ff1a1a")
            self.pin_var.set("")
            self.after(1500, lambda: self.info_label.configure(text="ESPERANDO RECONOCIMIENTO BIOMÉTRICO...", text_color="#00ffcc"))

    def unlock_system(self):
        if self.unlocked: return
        self.unlocked = True
        self.info_label.configure(text="IDENTIDAD CONFIRMADA. BIENVENIDO, SEÑOR.", text_color="#00ff00")
        self.header.configure(text="ACCESO CONCEDIDO", text_color="#00ff00")
        self.update()
        time.sleep(1) # Pequeña pausa estetica
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            
        # Ocultarnos en vez de matarnos
        self.withdraw()
        self.is_active = False
        
        try:
            with open(STATE_FILE, "w") as f:
                f.write("HIDE")
        except:
            pass

    def update_camera(self):
        if self.unlocked: return
        
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # Efecto espejo
            
            # Reconocimiento
            if self.model_loaded:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Deteccion
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(100, 100))
                
                for (x, y, w, h) in faces:
                    # Dibujar Rectangulo UI
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 204, 0), 2)
                    
                    # Predecir
                    id_, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
                    
                    # Mostrar confianza (menor es mejor en LBPH)
                    # Una distancia LBPH menor de 65 indica buena confidencia
                    if confidence < 65:
                        cv2.putText(frame, f"Nivel Macheo: {int(100 - confidence)}% - OK", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        self.unlock_system()
                        return # salimos para no procesar mas
                    else:
                        cv2.putText(frame, "DESCONOCIDO", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # --- RENDERIZADO VISUAL EN LA UI ---
            # Reducir tamaño del frame visualmente o aplicarle mascara
            display_frame = cv2.resize(frame, (400, 300))
            cv2image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            imgtk = ctk.CTkImage(light_image=img, size=(400, 300))
            self.video_label.configure(image=imgtk)
        else:
            # --- PROTECCIÓN CONTRA CORTE DE ENERGÍA USB (SUSPENSIÓN) ---
            # Si ret es False, la PC se durmió o la cámara se desconectó. 
            # Liberamos y forzamos reconexión inmediatamente para que retome al despertar
            self.cap.release()
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
        self.after(30, self.update_camera)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = JarvisLockScreen()
    app.mainloop()
