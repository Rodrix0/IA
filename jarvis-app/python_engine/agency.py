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

import httpx, re

CODER_MODEL   = "qwen2.5-coder:7b"
GENERAL_MODEL = "llama3.1:latest"
OLLAMA_URL    = "http://127.0.0.1:11434/api/generate"

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
# Agente 3 — CODER
# ─────────────────────────────────────────────────────────────────────────────

CODER_PROMPT = """You are the CODER AGENT — a 10x Senior Frontend Engineer.
Write the COMPLETE, SINGLE-FILE HTML page.

PROJECT REQUEST: {user_prompt}

ARCHITECT'S PLAN:
{architect_plan}

CSS DESIGN TOKENS (MUST USE EVERYWHERE):
{css_vars}

MANDATORY RULES:
1. Output ONLY raw HTML starting with <!DOCTYPE html>.
2. Build ALL CSS inside <style> using the provided CSS variables. Do not use default unstyled HTML! Every button, input, and div must look premium.
3. Import Google Fonts. Apply --font-display to headings and --font-body to text.
4. CRITICAL: THIS IS A STANDALONE MOCKUP. DO NOT use `fetch()` or external APIs to load data. HARDCODE a JavaScript array with at least 6 beautiful, realistic products and render them dynamically. Use Unsplash image URLs (https://images.unsplash.com/photo-...).
5. If a shopping cart is requested, implement the UI for it (e.g., a sliding sidebar or modal) and write inline JavaScript to make "Add to Cart" functional entirely in memory (update counters, show items, calculate total).
6. The layout MUST be responsive (Flexbox/Grid).
7. Ensure massive padding, modern UI patterns (glassmorphism, cards), and breathing room between sections.

OUTPUT: raw HTML only. NO markdown fences. NO explanations. DO NOT use placeholders like `<!-- existing code -->`. You MUST output the ENTIRE document from `<!DOCTYPE html>` to `</html>`!"""

async def run_coder(user_prompt: str, architect_plan: str, css_vars: str) -> str:
    print("[Agency]  Coder escribiendo HTML + JS...")
    prompt = CODER_PROMPT.format(
        user_prompt=user_prompt[:400],
        architect_plan=architect_plan[:2000],
        css_vars=css_vars[:800],
    )
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=7000, temperature=0.3)
    html = _clean_code(raw, "html")
    print(f"[Agency]  Coder OK — {len(html)} chars de HTML generados.")
    return html

# ─────────────────────────────────────────────────────────────────────────────
# Agente 4 — CREATIVE DIRECTOR
# ─────────────────────────────────────────────────────────────────────────────

DIRECTOR_PROMPT = """You are the CREATIVE DIRECTOR AGENT — an obsessive Art Director.
ELEVATE the following HTML page to world-class, jaw-dropping quality.

DESIGN TOKENS:
{css_vars}

ORIGINAL HTML:
{coder_html}

TASKS:
1. ADD CSS animations (fade-in, slide-up on scroll, smooth hover lifts with shadows).
2. ADD visual depth (glassmorphism for navbars/modals, gradients, subtle borders).
3. FIX any ugly or unstyled elements. Make sure buttons look clickable and premium (using --color-accent).
4. VERIFY all colors use CSS variables. 
5. POLISH typography: large heroic titles, readable line-heights.
6. IF there is a shopping cart or product grid, ensure the layout is immaculate.

CRITICAL:
- Output ONLY the final polished HTML. No explanation, no markdown fences.
- Keep ALL JavaScript and HTML content intact. DO NOT use placeholders like `<!-- existing content here -->`. YOU MUST OUTPUT THE ENTIRE FILE from `<!DOCTYPE html>` to `</html>`!
- Make it look like a $50,000 custom website."""


async def run_creative_director(css_vars: str, coder_html: str) -> str:
    print("[Agency]  Creative Director puliendo interfaz...")
    prompt = DIRECTOR_PROMPT.format(
        css_vars=css_vars[:800],
        coder_html=coder_html[:8000],
    )
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=8000, temperature=0.4)
    html = _clean_code(raw, "html")
    if "<html" not in html.lower():
        html = _clean_code(raw, "")
    # Si el director no devuelve HTML válido, quedarse con el del Coder
    if len(html) < 500 or "<html" not in html.lower():
        print("[Agency]  Director devolvio output invalido, usando HTML del Coder.")
        return coder_html
    print(f"[Agency]  Director OK — HTML final: {len(html)} chars.")
    return html


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR — run_agency()
# ─────────────────────────────────────────────────────────────────────────────

async def run_agency(user_prompt: str, design_md: str = "") -> dict:
    """
    Orquesta el pipeline completo de 4 agentes.

    Args:
        user_prompt: Descripción del proyecto (lo que el usuario le pidió a Jarvis).
        design_md:   Contenido del archivo DESIGN.md instalado en el proyecto.

    Returns:
        dict con keys:
          - html          : str — HTML final listo para guardar
          - css_vars      : str — tokens CSS del Stylist
          - architect_plan: str — plan del Architect
          - design_used   : bool
    """
    print("\n[Agency] ══════════════════════════════════════════════")
    print(f"[Agency] 🚀 Pipeline iniciado para: {user_prompt[:80]}")
    print("[Agency] ══════════════════════════════════════════════")

    # Stage 1 — Stylist
    css_vars = await run_stylist(user_prompt, design_md)

    # Stage 2 — Architect
    architect_plan = await run_architect(user_prompt, css_vars)

    # Stage 3 — Coder
    coder_html = await run_coder(user_prompt, architect_plan, css_vars)

    # Stage 4 — Creative Director
    final_html = await run_creative_director(css_vars, coder_html)

    print("[Agency] ✅ Pipeline completo.")

    return {
        "html":           final_html,
        "css_vars":       css_vars,
        "architect_plan": architect_plan,
        "design_used":    bool(design_md),
    }
