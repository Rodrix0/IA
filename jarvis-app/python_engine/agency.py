# -*- coding: utf-8 -*-
"""
agency.py — Sistema Multi-Agente de Diseño Web para Jarvis
============================================================
4 agentes en pipeline:
  1. Stylist          → Define tokens CSS desde el DESIGN.md
  2. Architect        → Planifica la estructura de componentes
  3. Coder            → Escribe HTML + JS funcional
  4. Creative Director → Pule animaciones, sombras y coherencia visual
"""

import httpx, re, json, os, base64

CODER_MODEL   = "qwen2.5-coder:7b"
GENERAL_MODEL = "llama3.1:latest"
OLLAMA_URL    = "http://127.0.0.1:11434/api/generate"
FORGE_URL     = "http://127.0.0.1:7860/sdapi/v1/txt2img"

# ─────────────────────────────────────────────────────────────────────────────
# Contrato de IDs compartido entre Coder y Scripter
# ─────────────────────────────────────────────────────────────────────────────

UI_CONTRACT = """
MANDATORY DOM IDs:
- Cart Count Badge: 'cart-count'
- Cart Sidebar Container: 'cart-sidebar'
- Cart Items List: 'cart-items-container'
- Total Price Display: 'cart-total'
- Checkout Button: 'btn-checkout'

MANDATORY CLASSES:
- Add to Cart Buttons: 'btn-add' (must have data-id, data-name, data-price)
- Open Cart Trigger: 'btn-open-cart'
"""

# ─────────────────────────────────────────────────────────────────────────────
# Generador de imagenes fisicas via Forge/Stable Diffusion
# ─────────────────────────────────────────────────────────────────────────────

UNSPLASH_FALLBACKS = [
    "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1514432324607-a09d9b4aefda?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&h=400&fit=crop",
]

async def generar_imagen_fisica(prompt: str, filename: str, project_path: str) -> str:
    """Llama a Forge (RTX 3050) para crear imagen real. Fallback a Unsplash."""
    payload = {
        "prompt": f"{prompt}, professional photography, 4k, highly detailed",
        "negative_prompt": "blurry, low quality, text, watermark",
        "steps": 20, "width": 512, "height": 512,
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            res = await client.post(FORGE_URL, json=payload)
            if res.status_code == 200:
                img_data = res.json()["images"][0]
                assets_dir = os.path.join(project_path, "assets")
                os.makedirs(assets_dir, exist_ok=True)
                with open(os.path.join(assets_dir, filename), "wb") as f:
                    f.write(base64.b64decode(img_data))
                print(f"[Agency] Imagen generada con GPU: assets/{filename}")
                return f"assets/{filename}"
    except Exception as e:
        print(f"[Agency] Forge no disponible ({e}), usando Unsplash fallback.")
    # Fallback
    idx = hash(filename) % len(UNSPLASH_FALLBACKS)
    return UNSPLASH_FALLBACKS[idx]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _call_llm(prompt: str, model: str = CODER_MODEL,
                    max_tokens: int = 3000, temperature: float = 0.3) -> str:
    """Llama a Ollama de forma asíncrona y devuelve el texto generado."""
    try:
        async with httpx.AsyncClient(timeout=240) as client:
            res = await client.post(OLLAMA_URL, json={
                "model":  model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            })
            return res.json().get("response", "").strip()
    except Exception as e:
        print(f"[Agency] LLM error: {e}")
        return ""


def _clean_code(raw: str, lang: str = "html") -> str:
    """Extrae el contenido de un bloque markdown, o devuelve el string limpio."""
    # Buscar bloque de codigo específico
    if lang:
        pattern = rf"```(?:{lang})?\s*(.*?)\s*```"
    else:
        pattern = r"```(?:\w+)?\s*(.*?)\s*```"
    
    match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Si no hay bloque markdown, intentar extraer desde <!DOCTYPE o <html hasta </html>
    low = raw.lower()
    start = low.find("<!doctype html>")
    if start == -1:
        start = low.find("<html")
    
    if start != -1:
        end = low.rfind("</html>")
        if end != -1:
            return raw[start:end+7].strip()
        return raw[start:].strip()
        
    return raw.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agente 1 — STYLIST
# ─────────────────────────────────────────────────────────────────────────────

STYLIST_PROMPT = """You are the STYLIST AGENT — an elite, award-winning UI/UX Designer.
Your ONLY job is to output a complete CSS :root block with design tokens.

INPUT — DESIGN.md specification (if any):
{design_md}

PROJECT REQUEST:
{user_prompt}

YOUR MISSION:
- If DESIGN.md is provided, use its colors but expand them into a fully robust design system.
- If DESIGN.md is empty or lacks details, INVENT a stunning, premium color palette perfectly suited for the project (e.g., if it's a coffee shop, use rich espresso browns, warm creams, and elegant gold accents).
- Output ONLY a CSS :root block. NO markdown fences, NO explanation.

Define ALL of these variables to create depth and modern aesthetics:
  --color-bg          (main page background)
  --color-surface     (card / component background, distinct from bg)
  --color-surface-2   (subtle variant for hover states or inputs)
  --color-accent      (primary brand / call-to-action color)
  --color-accent-hover
  --color-text        (main readable text)
  --color-text-muted  (secondary / caption text)
  --color-border      (dividers and subtle card borders)
  --font-display      (headline font - e.g., 'Playfair Display', 'Orbitron')
  --font-body         (body font - e.g., 'Inter', 'Roboto')
  --radius-sm         (e.g., 4px)
  --radius-md         (e.g., 12px)
  --radius-lg         (e.g., 24px or 50% for pills)
  --shadow-sm         (subtle shadow for depth)
  --shadow-md         (medium shadow for cards)
  --shadow-lg         (dramatic shadow for modals/dropdowns)
  --transition        (e.g., 0.3s cubic-bezier(0.4, 0, 0.2, 1))
  --spacing-unit      (e.g., 1rem)
"""

async def run_stylist(user_prompt: str, design_md: str) -> str:
    print("[Agency] 🎨 Stylist definiendo tokens de diseño...")
    prompt = STYLIST_PROMPT.format(
        design_md=design_md[:3000] if design_md else "(No design spec provided. Please invent the most beautiful and appropriate palette for this project.)",
        user_prompt=user_prompt[:400],
    )
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=600, temperature=0.5)
    match = re.search(r":root\s*\{.*?\}", raw, re.DOTALL)
    if match:
        css_vars = match.group(0)
        print(f"[Agency] 🎨 Stylist OK — {css_vars.count('--')} variables definidas.")
        return css_vars
    print("[Agency] 🎨 Stylist fallback — usando tokens premium por defecto.")
    return """:root {
  --color-bg: #0a0a0a; --color-surface: #141414; --color-surface-2: #1f1f1f;
  --color-accent: #c9a96e; --color-accent-hover: #e8c98a;
  --color-text: #f0ede8; --color-text-muted: #9a9087; --color-border: #2a2a2a;
  --font-display: 'Playfair Display', serif; --font-body: 'Inter', sans-serif;
  --radius-sm: 8px; --radius-md: 16px; --radius-lg: 32px;
  --shadow-sm: 0 4px 6px rgba(0,0,0,0.3); --shadow-md: 0 10px 25px rgba(0,0,0,0.5);
  --shadow-lg: 0 25px 50px rgba(0,0,0,0.7); --transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --spacing-unit: 1rem;
}"""

# ─────────────────────────────────────────────────────────────────────────────
# Agente 2 — ARCHITECT
# ─────────────────────────────────────────────────────────────────────────────

ARCHITECT_PROMPT = """You are the ARCHITECT AGENT — a ruthless UX Strategist.
Plan the EXACT component structure for this web page. It must feel like a modern, premium web app (e.g., Apple, Stripe, Vercel).

PROJECT REQUEST: {user_prompt}

CSS TOKENS AVAILABLE:
{css_vars}

DELIVER a structured plan in plain text with:
1. Google Fonts to import.
2. Layout strategy (CSS Grid/Flexbox expectations).
3. List of sections (Navbar, Hero, Dynamic Content like Shopping Cart/Products, Footer).
4. For EACH section: specify the exact UI components needed (e.g., "Product Card with image, price, and 'Add to Cart' button", "Floating Cart Sidebar").
5. Global interactions (e.g., smooth scrolling, cart modal toggle).

If the user asks for a store/cart, heavily emphasize the UI for products and the shopping cart experience.
NO CODE. Just the architecture plan in English."""

async def run_architect(user_prompt: str, css_vars: str) -> str:
    print("[Agency]  Architect planificando estructura...")
    prompt = ARCHITECT_PROMPT.format(
        user_prompt=user_prompt[:500],
        css_vars=css_vars[:800],
    )
    plan = await _call_llm(prompt, model=CODER_MODEL, max_tokens=1200, temperature=0.4)
    print(f"[Agency]  Architect OK — plan de {len(plan)} chars.")
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# Agente 3 — CODER (Solo Diseno Visual)
# ─────────────────────────────────────────────────────────────────────────────

CODER_PROMPT = """You are the LEAD UI DEVELOPER. Build a premium interface.

PROJECT REQUEST: {user_prompt}

ARCHITECT'S PLAN:
{architect_plan}

CSS DESIGN TOKENS (INJECT THESE INTO THE HEAD):
{css_vars}

UI CONTRACT (YOU MUST USE THESE EXACT IDs AND CLASSES):
{ui_contract}

IMAGE PATHS TO USE:
{image_paths}

RULES:
1. Output ONLY raw HTML starting with <!DOCTYPE html>.
2. Use Tailwind CSS CDN: <script src="https://cdn.tailwindcss.com"></script>
3. Build a Hero Section, a Product Grid, and a Hidden Sidebar for the Shopping Cart.
4. Follow the UI CONTRACT above for all IDs and classes.
5. STYLE: Use glassmorphism, rounded-3xl, smooth transitions. Map CSS variables via Tailwind: bg-[var(--color-bg)], text-[var(--color-text)].
6. Use the IMAGE PATHS provided above for hero and products. DO NOT use via.placeholder.com.
7. Hardcode 4 product cards with realistic names, descriptions, prices.
8. DO NOT write any <script> logic. Add <script src="script.js"></script> before </body>.

OUTPUT: ONLY HTML/CSS. NO markdown fences. NO JavaScript logic."""

async def run_coder(user_prompt: str, architect_plan: str, css_vars: str,
                   image_paths: list = None) -> str:
    print("[Agency] Coder construyendo interfaz visual...")
    paths_str = "\n".join(f"- Image {i+1}: {p}" for i, p in enumerate(image_paths or []))
    if not paths_str:
        paths_str = "Use Unsplash coffee images."
    prompt = CODER_PROMPT.format(
        user_prompt=user_prompt[:400],
        architect_plan=architect_plan[:2000],
        css_vars=css_vars[:800],
        ui_contract=UI_CONTRACT,
        image_paths=paths_str,
    )
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=7000, temperature=0.3)
    html = _clean_code(raw, "html")
    print(f"[Agency] Coder OK -- {len(html)} chars de HTML generados.")
    return html


# ─────────────────────────────────────────────────────────────────────────────
# Agente 4 — PHOTOGRAPHER (Conceptos Visuales para Stable Diffusion)
# ─────────────────────────────────────────────────────────────────────────────

PHOTOGRAPHER_PROMPT = """You are the VISUAL CONTENT DIRECTOR.
Based on the project: {user_prompt}, identify 4 key images needed (e.g., hero_bg, product_1, product_2, product_3).
For each image, write a highly detailed artistic prompt for Stable Diffusion.
Output ONLY a JSON list like this:
[{{"name": "hero.png", "prompt": "high quality coffee shop interior, cinematic lighting..."}}, ...]
No markdown fences. No explanation. ONLY valid JSON."""

async def run_photographer(user_prompt: str) -> list:
    print("[Agency] Photographer creando conceptos visuales...")
    raw = await _call_llm(
        PHOTOGRAPHER_PROMPT.format(user_prompt=user_prompt[:400]),
        model=CODER_MODEL, max_tokens=800, temperature=0.5
    )
    try:
        cleaned = _clean_code(raw, "json")
        # Intentar parsear JSON
        prompts = json.loads(cleaned)
        print(f"[Agency] Photographer OK -- {len(prompts)} conceptos de imagen generados.")
        return prompts
    except Exception as e:
        print(f"[Agency] Photographer fallo parseando JSON: {e}")
        # Fallback: imagenes por defecto
        return [
            {"name": "hero.png", "prompt": "premium coffee shop interior, warm lighting, cinematic, 4k"},
            {"name": "product_1.png", "prompt": "artisan espresso coffee cup, steam, dark background, product photography"},
            {"name": "product_2.png", "prompt": "fresh croissant on rustic wooden table, bakery, warm tones"},
            {"name": "product_3.png", "prompt": "iced latte with milk swirl, glass cup, minimalist background"},
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Agente 5 — SCRIPTER (Solo Logica JS - State-Based)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPTER_PROMPT = f"""You are a SENIOR JS ENGINEER.
Create the logic for a state-based shopping cart.

CONTRACT TO FOLLOW:
{UI_CONTRACT}

HTML STRUCTURE PROVIDED:
{{coder_html}}

TASKS:
1. Initialize 'let cart = [];'.
2. Use Event Delegation: document.addEventListener('click', e => ... ) for '.btn-add' and '.btn-open-cart'.
3. Update LocalStorage on every cart change.
4. Function 'renderCart()' must clear and rebuild 'cart-items-container' using template literals.
5. All prices must be formatted with 2 decimals.
6. Update 'cart-count' badge and 'cart-total' on every change.
7. 'toggleCart()' must toggle 'cart-sidebar' visibility with translate-x transition.

OUTPUT: ONLY the JavaScript code. No explanations. No markdown fences. No <script> tags."""

async def run_scripter(coder_html: str) -> str:
    print("[Agency] Scripter programando logica funcional...")
    prompt = SCRIPTER_PROMPT.format(coder_html=coder_html[:6000])
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=2500, temperature=0.2)
    js = _clean_code(raw, "javascript")
    if not js or len(js) < 50:
        js = _clean_code(raw, "")
    js = re.sub(r'^\s*<script[^>]*>\s*', '', js, flags=re.IGNORECASE)
    js = re.sub(r'\s*</script>\s*$', '', js, flags=re.IGNORECASE)
    print(f"[Agency] Scripter OK -- {len(js)} chars de JS generados.")
    return js


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR — run_agency()
# ─────────────────────────────────────────────────────────────────────────────

async def run_agency(user_prompt: str, design_md: str = "", project_path: str = "") -> dict:
    """
    Orquesta el pipeline de 5 agentes:
      Stylist -> Architect -> Coder -> Photographer -> Scripter

    Args:
        user_prompt: Descripcion del proyecto.
        design_md:   Contenido del archivo DESIGN.md instalado en el proyecto.

    Returns:
        dict con keys:
          - files         : dict[str, str] -- archivos a guardar {nombre: contenido}
          - html          : str -- HTML final (para compatibilidad)
          - css_vars      : str -- tokens CSS del Stylist
          - architect_plan: str -- plan del Architect
          - image_prompts : list -- prompts del Photographer para Stable Diffusion
          - design_used   : bool
    """
    print("\n[Agency] ====================================================")
    print(f"[Agency] Pipeline iniciado para: {user_prompt[:80]}")
    print("[Agency] ====================================================")

    # Stage 1 -- Stylist
    css_vars = await run_stylist(user_prompt, design_md)

    # Stage 2 -- Architect
    architect_plan = await run_architect(user_prompt, css_vars)

    # Stage 3 -- Photographer (genera imagenes ANTES que el Coder)
    image_prompts = await run_photographer(user_prompt)
    image_paths = []
    if project_path:
        for concept in image_prompts:
            ruta = await generar_imagen_fisica(
                concept["prompt"], concept["name"], project_path
            )
            image_paths.append(ruta)
    else:
        image_paths = UNSPLASH_FALLBACKS[:len(image_prompts)]

    # Stage 4 -- Coder (recibe las rutas reales de imagenes)
    coder_html = await run_coder(user_prompt, architect_plan, css_vars, image_paths)

    # Stage 5 -- Scripter (Solo Logica)
    logic_js = await run_scripter(coder_html)

    # ── Ensamblaje final ──────────────────────────────────────────────
    # Safety net: reemplazar placeholders rotos con Unsplash
    img_idx = [0]
    def _next_fallback(match):
        url = UNSPLASH_FALLBACKS[img_idx[0] % len(UNSPLASH_FALLBACKS)]
        img_idx[0] += 1
        return url
    coder_html = re.sub(r'https?://via\.placeholder\.com/[^"]*', _next_fallback, coder_html)

    # Asegurar que el HTML tenga el link a script.js
    if "script.js" not in coder_html:
        if "<!-- JS_HERE -->" in coder_html:
            coder_html = coder_html.replace(
                "<!-- JS_HERE -->",
                '<script src="script.js"></script>'
            )
        else:
            coder_html = coder_html.replace(
                "</body>",
                '<script src="script.js"></script>\n</body>'
            )

    files = {
        "index.html": coder_html,
        "script.js":  logic_js,
    }

    print(f"[Agency] Pipeline completo: {len(files)} archivos generados.")
    for fname, content in files.items():
        print(f"  -> {fname}: {len(content)} chars")

    return {
        "files":          files,
        "html":           coder_html,
        "css_vars":       css_vars,
        "architect_plan": architect_plan,
        "image_prompts":  image_prompts,
        "design_used":    bool(design_md),
    }
