import os, json, subprocess, httpx

WORKSPACE = os.path.join(os.path.expanduser("~"), "Desktop", "Jarvis_Projects")
if not os.path.exists(WORKSPACE): os.makedirs(WORKSPACE)

# Archivo de sesión para persistir el proyecto activo entre reinicios
SESSION_FILE = os.path.join(WORKSPACE, ".jarvis_session.json")

def _save_session(project_name: str):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"active_project": project_name}, f)

def _load_session() -> str | None:
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("active_project")
        except Exception:
            return None
    return None

# ─────────────────────────────────────────────
# PALETAS DE COLOR DISPONIBLES
# ─────────────────────────────────────────────
PALETAS = {
    "cafe_dorado": {
        "nombre": "Café Dorado (default)",
        "accent": "#C9A96E", "accent_light": "#E8C98A", "accent_dark": "#8B6914",
        "bg": "#0D0D0D", "bg2": "#1A1A1A", "bg3": "#252525",
        "text": "#F0EDE8", "text_muted": "#9A9087",
        "font_title": "Playfair Display", "font_body": "Inter",
        "keywords": ["cafe", "cafetería", "restaurant", "comida", "bar", "cerveza", "vino", "gourmet"]
    },
    "neon_tech": {
        "nombre": "Neon Tech",
        "accent": "#00F5FF", "accent_light": "#80FAFF", "accent_dark": "#00A8B5",
        "bg": "#070B14", "bg2": "#0D1321", "bg3": "#141D2E",
        "text": "#E0F4FF", "text_muted": "#5A7A99",
        "font_title": "Orbitron", "font_body": "Rajdhani",
        "keywords": ["tecnología", "tech", "software", "app", "saas", "startup", "sistema", "plataforma", "inteligencia", "ia", "robot"]
    },
    "verde_naturaleza": {
        "nombre": "Verde Naturaleza",
        "accent": "#4CAF50", "accent_light": "#81C784", "accent_dark": "#2E7D32",
        "bg": "#0A1A0A", "bg2": "#112211", "bg3": "#1A2E1A",
        "text": "#E8F5E9", "text_muted": "#6A9B6E",
        "font_title": "Lora", "font_body": "Inter",
        "keywords": ["eco", "naturaleza", "verde", "orgánico", "planta", "jardín", "sostenible", "salud", "gym", "deporte", "fitness"]
    },
    "violeta_creativo": {
        "nombre": "Violeta Creativo",
        "accent": "#9C27B0", "accent_light": "#CE93D8", "accent_dark": "#6A1B9A",
        "bg": "#0D0514", "bg2": "#14082B", "bg3": "#1E0E3A",
        "text": "#F3E5F5", "text_muted": "#9575CD",
        "font_title": "Playfair Display", "font_body": "Inter",
        "keywords": ["arte", "diseño", "creativo", "agencia", "portfolio", "música", "moda", "estudio", "galería"]
    },
    "rojo_impacto": {
        "nombre": "Rojo Impacto",
        "accent": "#F44336", "accent_light": "#EF9A9A", "accent_dark": "#B71C1C",
        "bg": "#0D0000", "bg2": "#1A0505", "bg3": "#260808",
        "text": "#FFEBEE", "text_muted": "#EF9A9A",
        "font_title": "Bebas Neue", "font_body": "Inter",
        "keywords": ["marketing", "ventas", "urgente", "oferta", "promoción", "descuento", "impacto", "deporte", "juego"]
    },
    "azul_corporativo": {
        "nombre": "Azul Corporativo",
        "accent": "#1976D2", "accent_light": "#64B5F6", "accent_dark": "#0D47A1",
        "bg": "#030912", "bg2": "#071525", "bg3": "#0C1F38",
        "text": "#E3F2FD", "text_muted": "#5C8BB0",
        "font_title": "Roboto Slab", "font_body": "Roboto",
        "keywords": ["empresa", "corporativo", "finanzas", "banco", "seguros", "legal", "consultoría", "negocios", "servicios"]
    },
    "blanco_minimalista": {
        "nombre": "Blanco Minimalista",
        "accent": "#212121", "accent_light": "#616161", "accent_dark": "#000000",
        "bg": "#FAFAFA", "bg2": "#F5F5F5", "bg3": "#EEEEEE",
        "text": "#212121", "text_muted": "#757575",
        "font_title": "Playfair Display", "font_body": "Inter",
        "keywords": ["minimalista", "limpio", "simple", "moderno", "portfolio personal", "blog", "médico", "clínica"]
    },
    "naranja_energia": {
        "nombre": "Naranja Energía",
        "accent": "#FF6F00", "accent_light": "#FFB74D", "accent_dark": "#E65100",
        "bg": "#0D0600", "bg2": "#1A0E00", "bg3": "#261500",
        "text": "#FFF8E1", "text_muted": "#FFCC80",
        "font_title": "Montserrat", "font_body": "Inter",
        "keywords": ["energía", "construcción", "inmobiliaria", "logística", "transporte", "delivery", "comida rápida", "hamburguesa"]
    }
}

def detect_palette(prompt: str, palette_override: str = None) -> dict:
    """Elige la paleta más apropiada para el proyecto."""
    if palette_override:
        key = palette_override.lower().replace(" ", "_")
        if key in PALETAS:
            return PALETAS[key]
        # Búsqueda parcial por nombre
        for k, v in PALETAS.items():
            if palette_override.lower() in v["nombre"].lower() or palette_override.lower() in k:
                return PALETAS[k]

    # Detección automática por palabras clave del prompt
    low = prompt.lower()
    best_palette = "cafe_dorado"
    best_score = 0
    for key, paleta in PALETAS.items():
        score = sum(1 for kw in paleta["keywords"] if kw in low)
        if score > best_score:
            best_score = score
            best_palette = key
    return PALETAS[best_palette]


PREMIUM_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;600&family=Orbitron:wght@400;700&family=Rajdhani:wght@400;600&family=Lora:wght@400;700&family=Bebas+Neue&family=Montserrat:wght@400;700&family=Roboto+Slab:wght@400;700&family=Roboto:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --accent: {palette_accent};
    --accent-light: {palette_accent_light};
    --accent-dark: {palette_accent_dark};
    --dark: {palette_bg};
    --dark2: {palette_bg2};
    --dark3: {palette_bg3};
    --text: {palette_text};
    --text-muted: {palette_text_muted};
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{ font-family: '{palette_font_body}', sans-serif; background: var(--dark); color: var(--text); }}

  /* NAV */
  nav {{
    position: fixed; top: 0; width: 100%; z-index: 100;
    padding: 1.2rem 4rem;
    display: flex; justify-content: space-between; align-items: center;
    background: rgba(13,13,13,0.85); backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(201,169,110,0.2);
  }}
  .logo {{ font-family: '{palette_font_title}', serif; font-size: 1.6rem; color: var(--accent); letter-spacing: 2px; }}
  .nav-links a {{ color: var(--text-muted); text-decoration: none; margin-left: 2rem; font-size: 0.9rem; letter-spacing: 1px; text-transform: uppercase; transition: color .3s; }}
  .nav-links a:hover {{ color: var(--accent); }}

  /* HERO */
  .hero {{
    min-height: 100vh;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    text-align: center;
    background: linear-gradient(135deg, #0D0D0D 0%, #1C1209 50%, #0D0D0D 100%);
    position: relative; overflow: hidden; padding: 2rem;
  }}
  .hero::before {{
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse at center, rgba(201,169,110,0.08) 0%, transparent 70%);
  }}
  .hero-badge {{
    font-size: 0.75rem; letter-spacing: 4px; text-transform: uppercase;
    color: var(--gold); border: 1px solid rgba(201,169,110,0.4);
    padding: .5rem 1.5rem; border-radius: 50px; margin-bottom: 2rem;
    animation: fadeDown .8s ease;
  }}
  .hero h1 {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(3rem, 8vw, 6rem); font-weight: 700; line-height: 1.1;
    background: linear-gradient(135deg, var(--gold-light), var(--gold), #8B6914);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    animation: fadeDown .8s ease .1s both;
  }}
  .hero p {{
    max-width: 600px; font-size: 1.1rem; color: var(--text-muted);
    margin: 1.5rem auto 2.5rem; line-height: 1.8;
    animation: fadeDown .8s ease .2s both;
  }}
  .hero-btns {{ display: flex; gap: 1rem; animation: fadeDown .8s ease .3s both; }}
  .btn-primary {{
    background: linear-gradient(135deg, var(--gold), #8B6914);
    color: #0D0D0D; font-weight: 600; padding: .9rem 2.2rem;
    border: none; border-radius: 8px; cursor: pointer; font-size: 1rem;
    letter-spacing: 1px; transition: transform .2s, box-shadow .2s;
  }}
  .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(201,169,110,0.4); }}
  .btn-outline {{
    background: transparent; color: var(--gold);
    padding: .9rem 2.2rem; border: 1px solid var(--gold);
    border-radius: 8px; cursor: pointer; font-size: 1rem; transition: all .2s;
  }}
  .btn-outline:hover {{ background: rgba(201,169,110,0.1); }}

  /* STATS */
  .stats {{
    display: flex; justify-content: center; gap: 4rem;
    padding: 3rem 4rem; background: var(--dark2);
    border-top: 1px solid rgba(201,169,110,0.15);
    border-bottom: 1px solid rgba(201,169,110,0.15);
  }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-family: 'Playfair Display', serif; font-size: 2.5rem; color: var(--gold); }}
  .stat-label {{ font-size: .8rem; color: var(--text-muted); letter-spacing: 2px; text-transform: uppercase; margin-top: .3rem; }}

  /* SECTIONS */
  section {{ padding: 6rem 4rem; }}
  section:nth-child(even) {{ background: var(--dark2); }}
  .section-tag {{ font-size: .75rem; letter-spacing: 4px; text-transform: uppercase; color: var(--gold); margin-bottom: 1rem; }}
  .section-title {{ font-family: 'Playfair Display', serif; font-size: 2.5rem; margin-bottom: 1rem; }}
  .section-sub {{ color: var(--text-muted); max-width: 600px; line-height: 1.8; margin-bottom: 3rem; }}

  /* MESAS MAP */
  .mapa-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 1rem; max-width: 700px;
  }}
  .mesa {{
    aspect-ratio: 1; border-radius: 12px; display: flex; flex-direction: column;
    align-items: center; justify-content: center; cursor: pointer;
    border: 2px solid transparent; transition: all .3s; font-size: .85rem;
  }}
  .mesa.libre {{ background: rgba(201,169,110,0.1); border-color: rgba(201,169,110,0.4); color: var(--gold); }}
  .mesa.libre:hover {{ background: rgba(201,169,110,0.25); transform: scale(1.05); }}
  .mesa.ocupada {{ background: rgba(255,80,80,0.08); border-color: rgba(255,80,80,0.3); color: #ff6b6b; }}
  .mesa-icon {{ font-size: 1.5rem; margin-bottom: .3rem; }}

  /* MENU CARDS */
  .menu-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.5rem; }}
  .menu-card {{
    background: var(--dark3); border-radius: 16px; overflow: hidden;
    border: 1px solid rgba(201,169,110,0.1); transition: transform .3s, border-color .3s;
  }}
  .menu-card:hover {{ transform: translateY(-5px); border-color: rgba(201,169,110,0.4); }}
  .menu-card-img {{
    height: 160px; display: flex; align-items: center; justify-content: center;
    font-size: 4rem;
    background: linear-gradient(135deg, rgba(201,169,110,0.05), rgba(201,169,110,0.12));
  }}
  .menu-card-body {{ padding: 1.2rem; }}
  .menu-card-name {{ font-weight: 600; font-size: 1.05rem; margin-bottom: .3rem; }}
  .menu-card-desc {{ color: var(--text-muted); font-size: .85rem; line-height: 1.6; margin-bottom: 1rem; }}
  .menu-card-footer {{ display: flex; justify-content: space-between; align-items: center; }}
  .menu-price {{ color: var(--gold); font-size: 1.1rem; font-weight: 600; }}
  .btn-add {{
    background: var(--gold); color: #0D0D0D; border: none;
    width: 32px; height: 32px; border-radius: 8px; font-size: 1.2rem;
    cursor: pointer; transition: opacity .2s; font-weight: 700;
  }}
  .btn-add:hover {{ opacity: 0.8; }}

  /* TRACKING */
  .tracking-bar {{
    display: flex; align-items: center; gap: 0; max-width: 600px; margin: 2rem 0;
  }}
  .track-step {{
    flex: 1; text-align: center; position: relative;
  }}
  .track-step::after {{
    content: ''; position: absolute; top: 20px; left: 50%; width: 100%;
    height: 2px; background: rgba(201,169,110,0.2);
  }}
  .track-step:last-child::after {{ display: none; }}
  .track-circle {{
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto .8rem; font-size: 1rem; position: relative; z-index: 1;
    border: 2px solid rgba(201,169,110,0.3);
    background: var(--dark);
  }}
  .track-step.done .track-circle {{ background: var(--gold); border-color: var(--gold); color: #0D0D0D; }}
  .track-step.active .track-circle {{ border-color: var(--gold); color: var(--gold); box-shadow: 0 0 15px rgba(201,169,110,0.4); }}
  .track-label {{ font-size: .8rem; color: var(--text-muted); }}
  .track-step.done .track-label, .track-step.active .track-label {{ color: var(--gold); }}

  /* PAGO */
  .pago-card {{
    background: var(--dark3); border: 1px solid rgba(201,169,110,0.15);
    border-radius: 20px; padding: 2rem; max-width: 480px;
  }}
  .pago-total {{ font-size: 2rem; color: var(--gold); font-family: 'Playfair Display', serif; margin: 1rem 0; }}
  .pago-metodos {{ display: flex; gap: 1rem; margin: 1.5rem 0; }}
  .metodo {{
    flex: 1; padding: 1rem; border-radius: 12px; text-align: center;
    border: 2px solid rgba(201,169,110,0.2); cursor: pointer;
    font-size: .9rem; transition: all .2s;
  }}
  .metodo.selected {{ border-color: var(--gold); background: rgba(201,169,110,0.08); color: var(--gold); }}
  .metodo:hover {{ border-color: rgba(201,169,110,0.5); }}

  /* FOOTER */
  footer {{
    padding: 3rem 4rem; border-top: 1px solid rgba(201,169,110,0.15);
    display: flex; justify-content: space-between; align-items: center;
    background: var(--dark);
  }}
  .footer-logo {{ font-family: 'Playfair Display', serif; color: var(--gold); font-size: 1.4rem; }}
  .footer-text {{ color: var(--text-muted); font-size: .85rem; }}

  @keyframes fadeDown {{ from {{ opacity:0; transform:translateY(-20px); }} to {{ opacity:1; transform:translateY(0); }} }}

  @media (max-width: 768px) {{
    nav {{ padding: 1rem 1.5rem; }}
    section {{ padding: 4rem 1.5rem; }}
    .stats {{ gap: 2rem; padding: 2rem 1.5rem; flex-wrap: wrap; }}
    .hero-btns {{ flex-direction: column; align-items: center; }}
    footer {{ flex-direction: column; gap: 1rem; text-align: center; }}
  }}
</style>
</head>
<body>

<nav>
  <div class="logo">{project_title}</div>
  <div class="nav-links">
    <a href="#inicio">Inicio</a>
    <a href="#mesas">Reservas</a>
    <a href="#menu">Menú</a>
    <a href="#seguimiento">Mi Pedido</a>
    <a href="#pago">Pagar</a>
  </div>
</nav>

<!-- HERO -->
<section class="hero" id="inicio">
  <div class="hero-badge">☕ Experiencia Premium de Café</div>
  <h1>{project_title}</h1>
  <p>{hero_description}</p>
  <div class="hero-btns">
    <button class="btn-primary" onclick="document.getElementById('mesas').scrollIntoView({{behavior:'smooth'}})">Reservar Mesa</button>
    <button class="btn-outline" onclick="document.getElementById('menu').scrollIntoView({{behavior:'smooth'}})">Ver Menú</button>
  </div>
</section>

<!-- STATS -->
<div class="stats">
  <div class="stat"><div class="stat-num">48</div><div class="stat-label">Mesas</div></div>
  <div class="stat"><div class="stat-num">{menu_count}+</div><div class="stat-label">Especialidades</div></div>
  <div class="stat"><div class="stat-num">4.9★</div><div class="stat-label">Calificación</div></div>
  <div class="stat"><div class="stat-num">15m</div><div class="stat-label">Tiempo promedio</div></div>
</div>

<!-- MESAS -->
<section id="mesas">
  <div class="section-tag">Plano del local</div>
  <h2 class="section-title">Reservá tu Mesa</h2>
  <p class="section-sub">Seleccioná una mesa disponible. Las mesas en dorado están libres, las rojas ya tienen reserva.</p>
  <div class="mapa-grid" id="mesaGrid"></div>
  <br>
  <button class="btn-primary" onclick="confirmarReserva()" style="margin-top:1rem;">Confirmar Reserva</button>
</section>

<!-- MENU -->
<section id="menu">
  <div class="section-tag">Nuestras Especialidades</div>
  <h2 class="section-title">El Menú</h2>
  <p class="section-sub">Seleccioná tus favoritos y los enviamos directo a tu mesa.</p>
  <div class="menu-grid" id="menuGrid"></div>
</section>

<!-- SEGUIMIENTO -->
<section id="seguimiento">
  <div class="section-tag">Estado en tiempo real</div>
  <h2 class="section-title">Seguí tu Pedido</h2>
  <p class="section-sub">Mirá en qué etapa está tu pedido sin tener que preguntar.</p>
  <div class="tracking-bar">
    <div class="track-step done">
      <div class="track-circle">✓</div>
      <div class="track-label">Confirmado</div>
    </div>
    <div class="track-step done">
      <div class="track-circle">✓</div>
      <div class="track-label">En preparación</div>
    </div>
    <div class="track-step active">
      <div class="track-circle">☕</div>
      <div class="track-label">Casi listo</div>
    </div>
    <div class="track-step">
      <div class="track-circle">🚀</div>
      <div class="track-label">En camino</div>
    </div>
    <div class="track-step">
      <div class="track-circle">✅</div>
      <div class="track-label">Entregado</div>
    </div>
  </div>
  <p style="color: var(--text-muted); margin-top:1rem;">Tiempo estimado de espera: <span style="color:var(--gold); font-weight:600;">~12 minutos</span></p>
</section>

<!-- PAGO -->
<section id="pago">
  <div class="section-tag">Checkout rápido</div>
  <h2 class="section-title">Pagar el Pedido</h2>
  <div class="pago-card">
    <p style="color:var(--text-muted);">Total a pagar</p>
    <div class="pago-total" id="totalDisplay">$0.00</div>
    <div style="border-top: 1px solid rgba(201,169,110,0.15); padding-top:1.5rem;">
      <p style="font-size:.9rem; color:var(--text-muted); margin-bottom:.8rem;">Método de pago</p>
      <div class="pago-metodos">
        <div class="metodo selected" onclick="selectMetodo(this)">💳 Tarjeta</div>
        <div class="metodo" onclick="selectMetodo(this)">📱 MercadoPago</div>
        <div class="metodo" onclick="selectMetodo(this)">💵 Efectivo</div>
      </div>
    </div>
    <button class="btn-primary" style="width:100%; margin-top:1rem;" onclick="procesarPago()">Pagar Ahora</button>
  </div>
</section>

<footer>
  <div class="footer-logo">{project_title}</div>
  <div class="footer-text">© 2026 · Todos los derechos reservados</div>
</footer>

<script>
const MENU_DATA = {menu_json};
const carrito = {{}};
let mesaSeleccionada = null;

// Generar mesas
const mesaGrid = document.getElementById('mesaGrid');
for (let i = 1; i <= 24; i++) {{
  const libre = Math.random() > 0.35;
  const el = document.createElement('div');
  el.className = `mesa ${{libre ? 'libre' : 'ocupada'}}`;
  el.innerHTML = `<span class="mesa-icon">${{libre ? '🪑' : '🔴'}}</span>Mesa ${{i}}`;
  if (libre) el.onclick = () => {{ mesaSeleccionada = i; document.querySelectorAll('.mesa.libre').forEach(m=>m.style.outline=''); el.style.outline='2px solid var(--gold)'; }};
  mesaGrid.appendChild(el);
}}

// Generar menú
const menuGrid = document.getElementById('menuGrid');
MENU_DATA.forEach(item => {{
  carrito[item.nombre] = 0;
  menuGrid.innerHTML += `
    <div class="menu-card">
      <div class="menu-card-img">${{item.emoji}}</div>
      <div class="menu-card-body">
        <div class="menu-card-name">${{item.nombre}}</div>
        <div class="menu-card-desc">${{item.descripcion}}</div>
        <div class="menu-card-footer">
          <span class="menu-price">$${{item.precio}}</span>
          <button class="btn-add" onclick="agregarAlCarrito('${{item.nombre}}', ${{item.precio}})">+</button>
        </div>
      </div>
    </div>`;
}});

function agregarAlCarrito(nombre, precio) {{
  carrito[nombre] = (carrito[nombre] || 0) + 1;
  calcularTotal();
  const btn = event.target;
  btn.textContent = carrito[nombre];
  btn.style.background = '#C9A96E';
}}

function calcularTotal() {{
  let total = 0;
  MENU_DATA.forEach(i => {{ total += (carrito[i.nombre] || 0) * i.precio; }});
  document.getElementById('totalDisplay').textContent = '$' + total.toFixed(2);
}}

function confirmarReserva() {{
  if (!mesaSeleccionada) {{ alert('Por favor seleccioná una mesa primero.'); return; }}
  alert(`✅ Reserva confirmada para Mesa ${{mesaSeleccionada}}. Tu código es: BH-${{Math.floor(Math.random()*9000)+1000}}`);
}}

function selectMetodo(el) {{
  document.querySelectorAll('.metodo').forEach(m => m.classList.remove('selected'));
  el.classList.add('selected');
}}

function procesarPago() {{
  const total = document.getElementById('totalDisplay').textContent;
  if (total === '$0.00') {{ alert('Agregá al menos un item al carrito.'); return; }}
  alert(`✅ Pago procesado por ${{total}}. ¡Gracias por elegir {project_title}!`);
}}
</script>
</body>
</html>"""

class JarvisDeveloper:
    def __init__(self):
        # Recuperar el proyecto activo de la sesión anterior
        self.active_project = _load_session()
        if self.active_project:
            print(f"[Jarvis Developer] 📂 Sesión recuperada: proyecto activo = '{self.active_project}'")

    async def execute_full_project(self, big_prompt: str):
        print("[Jarvis Architect] 🏗️ Generando proyecto premium...")

        content_prompt = f"""
        Analiza este proyecto y devuelve SOLO un JSON con esta estructura exacta:
        {{
            "project_name": "brewhub_app",
            "project_title": "BrewHub",
            "hero_description": "Una descripción elegante de 2 oraciones para la cafetería.",
            "menu": [
                {{"nombre": "Espresso", "descripcion": "Café intenso de origen único", "precio": 350, "emoji": "☕"}},
                {{"nombre": "Cappuccino", "descripcion": "Espuma suave con leche cremosa", "precio": 450, "emoji": "🍵"}},
                {{"nombre": "Croissant", "descripcion": "Hojaldrado, mantecoso y crujiente", "precio": 280, "emoji": "🥐"}},
                {{"nombre": "Tostado Especial", "descripcion": "Pan de masa madre con ingredientes premium", "precio": 520, "emoji": "🥪"}},
                {{"nombre": "Americano", "descripcion": "Café largo suave y aromático", "precio": 320, "emoji": "☕"}},
                {{"nombre": "Cheesecake", "descripcion": "Postre cremoso con frutos rojos", "precio": 680, "emoji": "🍰"}}
            ]
        }}

        PROYECTO: {big_prompt[:800]}
        """

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                res = await client.post("http://127.0.0.1:11434/api/generate",
                    json={
                        "model": "llama3.1:latest",
                        "prompt": content_prompt,
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1}
                    })
                data = json.loads(res.json().get("response", "{}"))
        except Exception as e:
            data = {
                "project_name": "brewhub_app",
                "project_title": "BrewHub",
                "hero_description": "Reservá tu mesa, pedí tu favorito y pagá sin esperas. La cafetería que se adapta a vos.",
                "menu": [
                    {"nombre": "Espresso", "descripcion": "Café intenso de origen único", "precio": 350, "emoji": "☕"},
                    {"nombre": "Cappuccino", "descripcion": "Espuma suave con leche cremosa", "precio": 450, "emoji": "🍵"},
                    {"nombre": "Croissant", "descripcion": "Hojaldrado, mantecoso y crujiente", "precio": 280, "emoji": "🥐"},
                    {"nombre": "Tostado Especial", "descripcion": "Pan de masa madre con ingredientes premium", "precio": 520, "emoji": "🥪"},
                    {"nombre": "Americano", "descripcion": "Café largo suave y aromático", "precio": 320, "emoji": "☕"},
                    {"nombre": "Cheesecake", "descripcion": "Postre cremoso con frutos rojos", "precio": 680, "emoji": "🍰"}
                ]
            }

        # Adjuntamos el prompt original para que detect_palette analice el contexto
        data["_raw_prompt"] = big_prompt

        # Detectar si el usuario pidió explícitamente una paleta ("con paleta neon", "estilo azul corporativo")
        import re
        palette_match = re.search(r'(?:paleta|estilo|colores?)\s+([\w\s]+?)(?:\.|,|$)', big_prompt.lower())
        palette_override = palette_match.group(1).strip() if palette_match else None

        return self._deploy_to_windows(data, palette_override=palette_override)

    def _deploy_to_windows(self, data, palette_override=None):
        p_name = data.get("project_name", "brewhub_app")
        p_title = data.get("project_title", "BrewHub")
        hero_desc = data.get("hero_description", "La mejor experiencia de café de la ciudad.")
        menu = data.get("menu", [])

        # Seleccionar paleta: override manual > detección automática por contenido
        raw_prompt = data.get("_raw_prompt", p_title)
        paleta = detect_palette(raw_prompt, palette_override)
        print(f"[Jarvis Designer] 🎨 Paleta seleccionada: {paleta['nombre']}")

        self.active_project = p_name
        _save_session(p_name)
        p_path = os.path.join(WORKSPACE, p_name)
        if not os.path.exists(p_path): os.makedirs(p_path)

        html = PREMIUM_TEMPLATE.format(
            project_title=p_title,
            hero_description=hero_desc,
            menu_count=len(menu),
            menu_json=json.dumps(menu, ensure_ascii=False),
            palette_accent=paleta["accent"],
            palette_accent_light=paleta["accent_light"],
            palette_accent_dark=paleta["accent_dark"],
            palette_bg=paleta["bg"],
            palette_bg2=paleta["bg2"],
            palette_bg3=paleta["bg3"],
            palette_text=paleta["text"],
            palette_text_muted=paleta["text_muted"],
            palette_font_title=paleta["font_title"],
            palette_font_body=paleta["font_body"],
        )

        index_path = os.path.join(p_path, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

        os.system(f'start "" "{index_path}"')
        try:
            subprocess.Popen(f'code "{p_path}"', shell=True)
        except Exception:
            pass

        return f"Señor, '{p_title}' desplegado con paleta '{paleta['nombre']}'. Navegador y VS Code abiertos."

    async def edit_project(self, instruccion: str):
        """Edición quirúrgica: elimina con regex, agrega solo el snippet nuevo."""
        if not self.active_project:
            return "Señor, no hay proyecto activo. Cargá uno primero."
        index_path = os.path.join(WORKSPACE, self.active_project, "index.html")
        if not os.path.exists(index_path):
            return f"No encontré index.html en '{self.active_project}'."

        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        import re
        low = instruccion.lower()
        acciones = []

        # Mapa: palabra clave → patrón de la sección a eliminar
        SECCIONES = {
            "mesa": r'<section[^>]*id=["\']mesas["\'][^>]*>.*?</section>',
            "reserva": r'<section[^>]*id=["\']mesas["\'][^>]*>.*?</section>',
            "seguimiento": r'<section[^>]*id=["\']seguimiento["\'][^>]*>.*?</section>',
            "pago": r'<section[^>]*id=["\']pago["\'][^>]*>.*?</section>',
            "menu": r'<section[^>]*id=["\']menu["\'][^>]*>.*?</section>',
            "stats": r'<div[^>]*class=["\']stats["\'][^>]*>.*?</div>',
            "footer": r'<footer[^>]*>.*?</footer>',
        }

        # 1. Eliminar secciones
        if any(p in low for p in ["elimina", "eliminá", "elimines", "quita", "quitá", "saca", "sacá", "borra"]):
            for clave, patron in SECCIONES.items():
                if clave in low:
                    nuevo = re.sub(patron, '', html, flags=re.DOTALL | re.IGNORECASE)
                    if nuevo != html:
                        html = nuevo
                        acciones.append(f"eliminé '{clave}'")

        # 2. Agregar nuevo bloque — Llama genera SOLO el snippet (no el archivo completo)
        if any(p in low for p in ["agrega", "agregá", "añade", "añadí", "incluye", "pon ", "poné", "implementá"]):
            prompt = f"""Generá SOLO un bloque HTML (sin DOCTYPE ni html/head/body) para esto:
PEDIDO: {instruccion}
Usá variables CSS: --accent, --dark, --dark2, --dark3, --text, --text-muted.
Devolvé ÚNICAMENTE el HTML del bloque, nada más."""
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    res = await client.post("http://127.0.0.1:11434/api/generate",
                        json={"model": "llama3.1:latest", "prompt": prompt,
                              "stream": False, "options": {"temperature": 0.2, "num_predict": 1500}})
                    snippet = res.json().get("response", "").strip()
                snippet = re.sub(r'^```(?:html)?\n?', '', snippet, flags=re.IGNORECASE)
                snippet = re.sub(r'\n?```$', '', snippet).strip()
                if len(snippet) > 50:
                    insert_before = "</footer>" if "</footer>" in html else "</body>"
                    html = html.replace(insert_before, f"\n{snippet}\n{insert_before}", 1)
                    acciones.append("agregué el nuevo bloque")
            except Exception as e:
                acciones.append(f"error generando bloque: {e}")

        # 3. SEPARAR / DIVIDIR en archivos individuales
        if any(p in low for p in ["separ", "divid", "extraé", "extrae", "desglosa"]):
            p_path = os.path.join(WORKSPACE, self.active_project)
            # Extraemos cada sección y la guardamos en su propio archivo
            secciones_generadas = []
            for id_sec in ["inicio", "mesas", "menu", "seguimiento", "pago"]:
                patron = rf'<section[^>]*id=["\'{id_sec}["\'][^>]*>.*?</section>'
                match = re.search(patron, html, flags=re.DOTALL | re.IGNORECASE)
                if match:
                    contenido = match.group(0)
                    nombre_archivo = f"{id_sec}.html"
                    wrapper = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>{id_sec.capitalize()}</title>
<link rel="stylesheet" href="style.css"></head><body>
{contenido}
</body></html>"""
                    with open(os.path.join(p_path, nombre_archivo), "w", encoding="utf-8") as f:
                        f.write(wrapper)
                    secciones_generadas.append(nombre_archivo)
            if secciones_generadas:
                acciones.append(f"separé en archivos: {', '.join(secciones_generadas)}")
                os.system(f'start "" "{p_path}"')  # Abrir carpeta del proyecto

        # 4. FALLBACK GENÉRICO — Llama genera SOLO el resultado concreto
        if not acciones:
            prompt = f"""Eres un programador web experto. Tenés que hacer esto sobre un proyecto HTML:

INSTRUCCIÓN: {instruccion}

El proyecto usa estas variables CSS: --accent, --dark, --dark2, --dark3, --text, --text-muted.

Según la instrucción:
- Si hay que crear un archivo nuevo: generá SOLO el contenido HTML del archivo, sin explicaciones.
- Si hay que modificar CSS: generá SOLO el bloque <style> o las reglas CSS necesarias.
- Si hay que agregar algo: generá SOLO el bloque HTML a insertar.
NO expliques nada. NO saludes. Solo el código."""
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    res = await client.post("http://127.0.0.1:11434/api/generate",
                        json={"model": "llama3.1:latest", "prompt": prompt,
                              "stream": False, "options": {"temperature": 0.2, "num_predict": 1500}})
                    resultado = res.json().get("response", "").strip()
                resultado = re.sub(r'^```(?:html|css)?\n?', '', resultado, flags=re.IGNORECASE)
                resultado = re.sub(r'\n?```$', '', resultado).strip()
                if len(resultado) > 30:
                    # Guardamos como archivo separado o insertamos en html
                    if "<html" in resultado.lower():
                        # Es un archivo completo nuevo
                        nombre_nuevo = "nuevo_archivo.html"
                        out_path = os.path.join(WORKSPACE, self.active_project, nombre_nuevo)
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(resultado)
                        os.system(f'start "" "{out_path}"')
                        acciones.append(f"creé el archivo '{nombre_nuevo}'")
                    else:
                        # Es un snippet, lo insertamos en el index
                        insert_before = "</footer>" if "</footer>" in html else "</body>"
                        html = html.replace(insert_before, f"\n{resultado}\n{insert_before}", 1)
                        with open(index_path, "w", encoding="utf-8") as f:
                            f.write(html)
                        os.system(f'start "" "{index_path}"')
                        acciones.append("apliqué el cambio solicitado")
                else:
                    return "Señor, el modelo no generó un resultado válido. Reformulá el pedido."
            except Exception as e:
                return f"Error en fallback genérico: {e}"

        if acciones and any(a not in ["apliqué el cambio solicitado"] for a in acciones):
            # Para acciones de eliminar/agregar que modificaron el html principal
            if any(p in low for p in ["elimina", "eliminá", "elimines", "quita", "agrega", "agregá", "añade"]):
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(html)
                os.system(f'start "" "{index_path}"')

        return f"Listo, señor: {' | '.join(acciones)}." if acciones else "Señor, no pude detectar qué cambio hacer."

    def load_project_by_name(self, nombre: str) -> str:
        """Carga un proyecto existente por nombre para seguir trabajando sobre él."""
        # Limpiamos posibles artículos o comillas que diga el usuario
        nombre_limpio = nombre.strip().strip('"\"').replace(" ", "_").lower()

        # Buscamos la carpeta en el workspace (coincidencia parcial)
        candidatos = [
            d for d in os.listdir(WORKSPACE)
            if os.path.isdir(os.path.join(WORKSPACE, d))
            and not d.startswith('.')
            and nombre_limpio in d.lower()
        ]

        if not candidatos:
            proyectos = [d for d in os.listdir(WORKSPACE) if os.path.isdir(os.path.join(WORKSPACE, d)) and not d.startswith('.')]
            lista = ', '.join(proyectos) if proyectos else 'ninguno'
            return f"Señor, no encontré un proyecto que coincida con '{nombre}'. Proyectos disponibles: {lista}."

        proyecto = candidatos[0]  # tomamos el mejor match
        self.active_project = proyecto
        _save_session(proyecto)
        print(f"[Jarvis Developer] 📂 Proyecto cargado manualmente: '{proyecto}'")
        return f"Señor, cargué el proyecto '{proyecto}'. A partir de ahora trabajaré sobre ese archivo."


dev_jarvis = JarvisDeveloper()
