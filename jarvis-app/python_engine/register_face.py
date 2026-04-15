import cv2
import os
import json
import numpy as np

import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'backend', 'data')
MODEL_FILE = os.path.join(DATA_DIR, 'trainer.yml')
SECURITY_FILE = os.path.join(DATA_DIR, 'security.json')
CASCADE_FILE = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

def register_admin(pin):
    print("="*50)
    print(" JARVIS OS - SISTEMA DE SEGURIDAD BIOMÉTRICA ")
    print("="*50)
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    security_data = {"pin": pin}
    with open(SECURITY_FILE, 'w') as f:
        json.dump(security_data, f)
        
    print("\n[+] PIN guardado. Ahora registraremos tu firma facial.")
    print("Mírate a la cámara y mueve LIGERAMENTE la cabeza para capturar distintos ángulos.")
    print("Capturando 50 muestras...\n")
    
    detector = cv2.CascadeClassifier(CASCADE_FILE)
    cap = cv2.VideoCapture(0)
    
    samples = []
    labels = []
    count = 0
    
    while count < 50:
        ret, frame = cap.read()
        if not ret: continue
        
        # Invertimos como espejo
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            count += 1
            samples.append(gray[y:y+h, x:x+w])
            labels.append(1) # ID 1 para el Admin
            
            # Dibujar progreso
            cv2.putText(frame, f"Captura: {count}/50", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
        cv2.imshow("Registro Biometrico de JARVIS", frame)
        cv2.waitKey(100) # Breve pausa para capturar diferentes caras
        
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n[+] Muestras capturadas correctamente.")
    print("[*] Entrenando Red Neuronal LBPH... por favor espera.")
    
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(samples, np.array(labels))
    recognizer.write(MODEL_FILE)
    
    print(f"\n[✓] Rostro entrenado con éxito.")
    print(f"JARVIS ahora te reconocerá.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_pin = sys.argv[1]
    else:
        user_pin = input("Introduce un PIN de 4 dígitos para recuperación: ")
    register_admin(user_pin)
