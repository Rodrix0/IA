# 🤖 Jarvis Developer Engine — Guía de Uso

Motor de generación de proyectos web local, usando **Llama 3.1 8B** + templates premium.
Los proyectos se guardan en:

---

## 🚀 Comandos Principales

### 1. Crear un proyecto nuevo
```
Jarvis, quiero que programes esto → [tu descripción o prompt largo]
```
**Ejemplos:**
```
Jarvis, quiero que programes esto: una página de landing page para mi estudio de fotografía con portfolio y formulario de contacto.

Jarvis, quiero que programes esto → Página web para una clínica médica con turnos online, mapa de ubicación y listado de especialistas.

Jarvis, quiero que programes esto, estilo neon tech → Plataforma SaaS para gestión de inventario con dashboard y reportes.
```

---

### 2. Editar el proyecto activo
```
Jarvis, [comando de edición] + [qué querés cambiar]
```
**Palabras que activan el modo edición:**
`cambiá` · `modificá` · `agregá` · `quitá` · `mejorá` · `arreglá` · `editá` · `seguí trabajando` · `actualizá`

**Ejemplos:**
```
Jarvis, cambiá el color del hero a azul marino.
Jarvis, agregá una sección de testimonios de clientes.
Jarvis, mejorá la navbar, que sea más compacta.
Jarvis, quitá el tracker de pedidos.
Jarvis, arreglá el formulario de contacto, que tenga campo de teléfono.
```

---

### 3. Cargar un proyecto anterior (tras reinicio)
```
Jarvis, cargá el proyecto [nombre]
Jarvis, seguí con [nombre]
Jarvis, continuá con [nombre]
```
**Ejemplos:**
```
Jarvis, cargá el proyecto brewhub
Jarvis, seguí con clinica_medica
Jarvis, continuá con mi_portfolio
```
> 💡 La sesión se guarda automáticamente en `.jarvis_session.json`. Si reiniciás Uvicorn, al levantarse recuerda el último proyecto.

---

### 4. Elegir una paleta de colores manualmente
Agregá al final de tu pedido de programación:
```
...con paleta [nombre de paleta]
...estilo [nombre de paleta]
...colores [nombre de paleta]
```
**Ejemplos:**
```
Jarvis, quiero que programes esto con paleta neon tech → [descripción]
Jarvis, quiero que programes esto, estilo azul corporativo → [descripción]
Jarvis, quiero que programes esto colores verde naturaleza → [descripción]
```

---

## 🎨 Paletas Disponibles

| # | Nombre | Acento | Fondo | Fuentes | Ideal para... |
|---|--------|--------|-------|---------|---------------|
| 1 | **Café Dorado** *(default)* | `#C9A96E` Dorado | `#0D0D0D` Negro | Playfair + Inter | Cafeterías, restaurants, bares, gourmet |
| 2 | **Neon Tech** | `#00F5FF` Cyan | `#070B14` Azul noche | Orbitron + Rajdhani | Tech, software, SaaS, startups, IA |
| 3 | **Verde Naturaleza** | `#4CAF50` Verde | `#0A1A0A` Verde oscuro | Lora + Inter | Eco, fitness, salud, orgánico, jardín |
| 4 | **Violeta Creativo** | `#9C27B0` Violeta | `#0D0514` Morado oscuro | Playfair + Inter | Arte, diseño, música, moda, agencias |
| 5 | **Rojo Impacto** | `#F44336` Rojo | `#0D0000` Negro rojizo | Bebas Neue + Inter | Marketing, ventas, ofertas, deportes |
| 6 | **Azul Corporativo** | `#1976D2` Azul | `#030912` Azul marino | Roboto Slab + Roboto | Empresas, finanzas, legal, servicios |
| 7 | **Blanco Minimalista** | `#212121` Casi negro | `#FAFAFA` Blanco | Playfair + Inter | Blogs, clínicas, portfolios, médicos |
| 8 | **Naranja Energía** | `#FF6F00` Naranja | `#0D0600` Negro cálido | Montserrat + Inter | Construcción, delivery, logística |

### Detección Automática
Si no especificás paleta, Jarvis la elige según las palabras de tu prompt:

```
"cafetería"   → Café Dorado
"tecnología"  → Neon Tech
"fitness"     → Verde Naturaleza
"agencia"     → Violeta Creativo
"ventas"      → Rojo Impacto
"corporativo" → Azul Corporativo
"clínica"     → Blanco Minimalista
"delivery"    → Naranja Energía
```

---

## 📁 Estructura de Proyectos Generados

```
Jarvis_Projects/
├── .jarvis_session.json      ← Sesión activa (último proyecto)
├── brewhub_app/
│   └── index.html            ← App completa en un solo archivo
├── clinica_medica/
│   └── index.html
└── mi_portfolio/
    └── index.html
```

> Cada `index.html` es **100% standalone**: no necesita servidor, se abre directo en el navegador.

---

## ⚙️ Stack Técnico del Motor

| Componente | Descripción |
|---|---|
| **Llama 3.1 8B** vía Ollama | Genera el contenido (textos, menús, datos) en JSON |
| **Python Template Engine** | Inyecta el contenido en HTML/CSS premium pre-diseñado |
| **8 Paletas de color** | CSS Variables dinámicas por proyecto |
| **Google Fonts** | Todas las fuentes cargadas desde CDN automáticamente |
| **Session JSON** | Persiste el proyecto activo entre reinicios de Uvicorn |

---

## 🛠️ Archivos del Motor

| Archivo | Función |
|---|---|
| `developer_service.py` | Motor principal: paletas, template, generación, edición |
| `main.py` | Router FastAPI: detecta intención y despacha al motor |
| `JARVIS_DEVELOPER_README.md` | Este archivo |

---

*Generado por Jarvis Developer Engine · 2026*
