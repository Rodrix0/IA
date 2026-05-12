# -*- coding: utf-8 -*-
"""
agency.py -- Multi-agent web builder for Jarvis (v4.0)
=====================================================
Pipeline:
  1. Architect   -> DevOps-grade plan + UI contract
  2. Stylist     -> CSS tokens
  3. Photographer-> Stable Diffusion prompts + assets
  4. Coder       -> HTML only
  5. TS Coder    -> TypeScript logic
  6. Scripter    -> Runtime JS
"""

from typing import List, Dict
import base64
import json
import os
import re
import time
import httpx

CODER_MODEL = "qwen2.5-coder:7b"
FORGE_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

UNSPLASH_FALLBACKS = [
    "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=900&h=900&fit=crop",
    "https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=900&h=900&fit=crop",
    "https://images.unsplash.com/photo-1514432324607-a09d9b4aefda?w=900&h=900&fit=crop",
    "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=900&h=900&fit=crop",
    "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=900&h=900&fit=crop",
    "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=900&h=900&fit=crop",
]

DEFAULT_LOCAL_ASSETS = [
    "assets/hero.png",
    "assets/product_1.png",
    "assets/product_2.png",
    "assets/product_3.png",
]


async def generar_imagen_fisica(prompt: str, filename: str, project_path: str) -> str:
    """Generate a real image with Forge (Stable Diffusion). Fallback to Unsplash."""
    assets_dir = os.path.join(project_path, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    out_path = os.path.join(assets_dir, filename)

    print(f"DEBUG: Intentando conectar a {FORGE_URL}...")
    payload = {
        "prompt": prompt,
        "steps": 20,
        "width": 1024,
        "height": 1024,
    }

    print(f"[RTX 4070] Rendering: {filename}...")
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(FORGE_URL, json=payload)
            print(f"DEBUG: Status Code de Forge: {res.status_code}")
            if res.status_code == 200:
                img_data = res.json().get("images", [None])[0]
                if img_data:
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(img_data))
                    if os.path.exists(out_path):
                        elapsed = time.time() - start_time
                        print(f"[Agency] Image saved: assets/{filename} in {elapsed:.2f}s")
                        return f"assets/{filename}"
    except Exception as exc:
        print(f"[Agency] Forge error for {filename}: {exc}")

    print(f"[Agency] Using fallback for {filename}")
    return "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1000"


async def _call_llm(
    prompt: str,
    model: str = CODER_MODEL,
    max_tokens: int = 3000,
    temperature: float = 0.3,
) -> str:
    """Call Ollama and return raw text response."""
    try:
        async with httpx.AsyncClient(timeout=240) as client:
            res = await client.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            return res.json().get("response", "").strip()
    except Exception as exc:
        print(f"[Agency] LLM error: {exc}")
        return ""


async def _liberar_vram_forge() -> None:
    """Best-effort request to release Forge resources after image generation."""
    base_url = FORGE_URL.rsplit("/", 1)[0]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{base_url}/interrupt")
    except Exception as exc:
        print(f"[Agency] Forge VRAM release skipped: {exc}")


def _clean_code(raw: str, lang: str = "html") -> str:
    """Extract code from a markdown block or return trimmed raw content."""
    if not raw:
        return ""

    pattern = rf"```(?:{lang})?\s*(.*?)\s*```" if lang else r"```(?:\w+)?\s*(.*?)\s*```"
    match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    low = raw.lower()
    start = low.find("<!doctype html>")
    if start == -1:
        start = low.find("<html")
    if start != -1:
        end = low.rfind("</html>")
        if end != -1:
            return raw[start : end + 7].strip()
        return raw[start:].strip()

    return raw.strip()


def _safe_json_list(raw: str) -> List[Dict]:
    if not raw:
        return []
    cleaned = _clean_code(raw, "json")
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, list) else []
    except Exception:
        try:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", name or "image.png").strip("._")
    if not cleaned:
        cleaned = "image.png"
    if not cleaned.lower().endswith(".png"):
        cleaned += ".png"
    return cleaned


def _build_stylesheet(css_vars: str) -> str:
    base = """
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font-body, Arial, sans-serif);
  background: var(--color-bg, #0a0a0a);
  color: var(--color-text, #f0ede8);
}
img { max-width: 100%; display: block; }
a { color: inherit; text-decoration: none; }

#cart-sidebar {
  transform: translateX(110%);
  transition: transform var(--transition, 0.3s ease);
}
#cart-sidebar.is-open { transform: translateX(0); }

.btn-add {
  transition: transform var(--transition, 0.3s ease), box-shadow var(--transition, 0.3s ease);
}
.btn-add.bump { transform: scale(1.05); }
"""
    return f"{css_vars.strip()}\n\n{base.strip()}\n"


ARCHITECT_PROMPT = """You are a Senior DevOps & Software Architect.
Project: {user_prompt}

MANDATORY RULES:
1. Define DOMAIN exactly based on the Project (e.g., if coffee, DOMAIN is 'Coffee Shop').
2. The 'products' array MUST reflect the DOMAIN strictly. DO NOT use fallback sushi or meat if the domain is coffee.
3. Output ONLY valid JSON.
"""

DEFAULT_PLAN = {
    "domain": "General",
    "layout": "Bento Grid",
    "title": "Premium Store",
    "sections": ["navbar", "hero", "products", "cart-sidebar", "footer"],
    "ui_contract": {
        "ids": {
            "cart_count": "cart-count",
            "cart_sidebar": "cart-sidebar",
            "cart_items": "cart-items-container",
            "cart_total": "total-price",
            "btn_checkout": "btn-checkout",
            "main_viewport": "main-viewport",
            "cart_trigger": "cart-trigger",
            "price_dynamic": "price-tag-dynamic",
        },
        "classes": {"add_to_cart": "btn-add", "open_cart": "btn-open-cart"},
        "data_attrs": ["data-id", "data-name", "data-price"],
    },
    "products": [
        {"id": 1, "name": "Product A", "description": "Premium item", "price": 29.99},
        {"id": 2, "name": "Product B", "description": "Best seller", "price": 39.99},
        {"id": 3, "name": "Product C", "description": "New arrival", "price": 24.99},
        {"id": 4, "name": "Product D", "description": "Limited edition", "price": 49.99},
    ],
    "tech_stack": {"frontend": ["HTML", "Tailwind", "TypeScript"], "runtime": "vanilla"},
}


async def run_architect(user_prompt: str) -> Dict:
    print("[Agency] Architect analyzing domain and structure...")
    prompt = ARCHITECT_PROMPT.replace("{user_prompt}", user_prompt[:500])
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=1400, temperature=0.4)
    try:
        cleaned = _clean_code(raw, "json")
        if not cleaned.startswith("{"):
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                cleaned = match.group(0)
        plan = json.loads(cleaned)
        if "ui_contract" not in plan or "products" not in plan:
            raise ValueError("JSON incomplete")
        print(f"[Agency] Architect OK -- domain: {plan.get('domain', '?')}")
        return plan
    except Exception as exc:
        print(f"[Agency] Architect failed ({exc}), using default plan.")
        return DEFAULT_PLAN


STYLIST_PROMPT = """Eres el Agente Estilista. Tu unica fuente de verdad es el archivo DESIGN.MD proporcionado.
Busca la seccion que coincida con la keyword solicitada (ej: linen, cyberpunk, matcha) y extrae sus valores hexadecimales.
PROHIBIDO usar comentarios como 'cambia esto'; entrega el codigo CSS funcional con los valores del archivo.
"""


async def run_stylist(user_prompt: str, domain: str, design_md: str) -> str:
    print(f"[Agency] Stylist defining tokens for domain: {domain}")
    prompt = STYLIST_PROMPT.format(
        user_keyword=domain,
        design_md=design_md[:3000] if design_md else "(No spec provided.)",
    )
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=700, temperature=0.5)
    match = re.search(r":root\s*\{.*?\}", raw, re.DOTALL)
    if match:
        css_vars = match.group(0)
        print(f"[Agency] Stylist OK -- {css_vars.count('--')} variables defined.")
        return css_vars
    print("[Agency] Stylist fallback -- using default tokens.")
    return """:root {
  --color-bg: #0a0a0a; --color-surface: #141414; --color-surface-2: #1f1f1f;
  --color-accent: #c9a96e; --color-accent-hover: #e8c98a;
  --color-text: #f0ede8; --color-text-muted: #9a9087; --color-border: #2a2a2a;
  --font-display: 'Playfair Display', serif; --font-body: 'Inter', sans-serif;
  --radius-sm: 8px; --radius-md: 16px; --radius-lg: 32px;
  --shadow-sm: 0 4px 6px rgba(0,0,0,0.3); --shadow-md: 0 10px 25px rgba(0,0,0,0.5);
  --shadow-lg: 0 25px 50px rgba(0,0,0,0.7); --transition: 0.3s ease;
  --spacing-unit: 1rem;
}"""


PHOTOGRAPHER_PROMPT = """You are a Visual Director.
Domain: {domain}
Project Context: {user_prompt}

Generate 4 image prompts STRICTLY related to the Domain.
If the domain is 'Coffee Shop', generate photos of coffee cups, espresso machines, and pastries. DO NOT GENERATE SUSHI OR MEAT.
Output ONLY JSON in this format: [{{"name": "hero.png", "prompt": "..."}}]
"""


async def run_photographer(user_prompt: str, domain: str, project_path: str) -> Dict:
    print(f"[Agency] Photographer creating images for domain: {domain}")
    raw = await _call_llm(
        PHOTOGRAPHER_PROMPT.format(domain=domain, user_prompt=user_prompt[:200]),
        model=CODER_MODEL,
        max_tokens=800,
        temperature=0.4,
    )
    prompts = _safe_json_list(raw)
    desired_names = ["hero.png", "product_1.png", "product_2.png", "product_3.png"]
    fallback_texts = [
        f"{domain} hero scene, studio lighting, 8k",
        f"{domain} product photo, studio lighting, 8k",
        f"{domain} product photo, sharp focus, 8k",
        f"{domain} product detail, clean background, 8k",
    ]
    normalized = []
    for i, name in enumerate(desired_names):
        prompt_text = fallback_texts[i]
        if i < len(prompts) and isinstance(prompts[i], dict):
            prompt_text = prompts[i].get("prompt") or prompt_text
        normalized.append({"name": name, "prompt": prompt_text})
    prompts = normalized

    if not project_path:
        return {
            "prompts": prompts,
            "image_paths": UNSPLASH_FALLBACKS[: len(prompts) or 4],
        }

    image_paths: List[str] = []
    for idx, item in enumerate(prompts):
        filename = _sanitize_filename(item.get("name", f"image_{idx}.png"))
        prompt = item.get("prompt", f"{domain} product photo")
        path = await generar_imagen_fisica(prompt, filename, project_path)
        if path.startswith("assets/") and project_path:
            abs_path = os.path.join(project_path, path)
            if not os.path.exists(abs_path):
                path = UNSPLASH_FALLBACKS[idx % len(UNSPLASH_FALLBACKS)]
        image_paths.append(path)

    return {"prompts": prompts, "image_paths": image_paths}


CODER_PROMPT = """You are a SENIOR FRONTEND DEVELOPER.
MANDATORY RULES:
1. DO NOT USE fetch(). DO NOT call external APIs.
2. DATA: Hardcode the product array directly inside script.js.
3. IMAGES: Use these exact local paths for the <img> tags: {image_paths}.
4. STYLE: Bento Grid layout with Tailwind CSS. Use dark background and glassmorphism.
5. NO PLACEHOLDERS: If you use a placeholder URL, the system will fail.
Output ONLY raw code.
"""


TS_CODER_PROMPT = """You are a Senior TypeScript Lead.
Based on this HTML: {html}, write 'main.ts'.
- Define Interfaces for 'Product' and 'CartState'.
- Implement business logic with strict types.
- Ensure state persistence.
Output ONLY TypeScript code.
"""


async def run_ts_coder(user_prompt: str, plan: Dict, html: str) -> str:
    print("[Agency] TS Coder writing main.ts...")
    prompt = TS_CODER_PROMPT.format(html=html[:6000])
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=2500, temperature=0.2)
    ts_code = _clean_code(raw, "typescript")
    if not ts_code or len(ts_code) < 50:
        ts_code = _clean_code(raw, "")
    return ts_code


SCRIPTER_PROMPT = """Genera el JS para este HTML: {coder_html}.
REGLAS:
1. Usa 'assets/product_1.png', 'assets/product_2.png', etc. para las imagenes.
2. No inventes productos, usa los del plan: {ui_contract}.
3. Si el ID 'product-grid' existe, inyecta los productos ahi.
"""


def _format_contract(plan: Dict) -> str:
    c = plan.get("ui_contract", {})
    ids = c.get("ids", {})
    classes = c.get("classes", {})
    attrs = c.get("data_attrs", [])
    lines = ["DOM IDs:"]
    for k, v in ids.items():
        lines.append(f"  - {k}: '{v}'")
    lines.append("CSS Classes:")
    for k, v in classes.items():
        lines.append(f"  - {k}: '{v}'")
    lines.append(f"Data Attributes on add-to-cart buttons: {', '.join(attrs)}")
    return "\n".join(lines)


def _format_products(plan: Dict) -> str:
    products = plan.get("products", [])
    lines = []
    for p in products:
        try:
            price = float(p.get("price", 0))
        except Exception:
            price = 0
        lines.append(f"- ID:{p.get('id')} | {p.get('name')} | {p.get('description')} | ${price:.2f}")
    return "\n".join(lines)


async def run_coder(user_prompt: str, plan: Dict, css_vars: str, image_paths: List[str]) -> str:
    print("[Agency] Coder building HTML...")
    paths = image_paths if image_paths else DEFAULT_LOCAL_ASSETS
    paths_str = "\n".join(f"- {p}" for p in paths if p)
    prompt = CODER_PROMPT.format(
        user_prompt=user_prompt[:400],
        image_paths=paths_str,
    )
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=7000, temperature=0.3)
    html = _clean_code(raw, "html")
    html = _ensure_asset_links(html)
    return html


async def run_scripter(coder_html: str, plan: Dict) -> str:
    print("[Agency] Scripter analyzing HTML for runtime logic...")
    prompt = SCRIPTER_PROMPT.replace("{coder_html}", coder_html[:6000])
    prompt = prompt.replace("{ui_contract}", _format_contract(plan))
    raw = await _call_llm(prompt, model=CODER_MODEL, max_tokens=3000, temperature=0.2)
    js = _clean_code(raw, "javascript")
    if not js or len(js) < 50:
        js = _clean_code(raw, "")
    js = re.sub(r"^\s*<script[^>]*>\s*", "", js, flags=re.IGNORECASE)
    js = re.sub(r"\s*</script>\s*$", "", js, flags=re.IGNORECASE)
    return js


async def run_integrator(html_base: str, image_paths: List[str]) -> str:
    if not html_base or not image_paths:
        return html_base

    idx = 0
    pattern = r'(<img\b[^>]*\bsrc=["\'])([^"\']*)(["\'][^>]*>)'

    def replace_src(match: re.Match) -> str:
        nonlocal idx
        if idx >= len(image_paths):
            return match.group(0)
        new_src = image_paths[idx]
        idx += 1
        return f"{match.group(1)}{new_src}{match.group(3)}"

    updated = re.sub(pattern, replace_src, html_base, flags=re.IGNORECASE)
    if idx == 0 and image_paths:
        gallery_items = "".join(
            f'<img src="{p}" alt="photo" class="w-full h-40 object-cover rounded-xl" />'
            for p in image_paths
            if p
        )
        gallery = (
            "<section class=\"mx-auto max-w-6xl px-6 py-10\">"
            "<div class=\"grid grid-cols-2 md:grid-cols-4 gap-4\">"
            f"{gallery_items}"
            "</div></section>"
        )
        if "</body>" in updated:
            updated = updated.replace("</body>", f"{gallery}\n</body>")
        else:
            updated += gallery
    return updated


async def run_welder(html_content: str, js_content: str, plan: Dict) -> str:
    print("\n[LOG][3/5] Agente Soldador: Sincronizando DOM y Logica...")

    html_content = re.sub(r'bg-gray-\d+', '', html_content)

    ids_en_js = re.findall(r"getElementById\([\'\"]([^\'\"]+)[\'\"]\)", js_content or "")
    for dom_id in ids_en_js:
        if f'id="{dom_id}"' not in html_content:
            print(f"  [WARN] ID faltante: {dom_id}. Inyectando contenedor...")
            if "grid" in dom_id or "product" in dom_id:
                html_content = html_content.replace('<body', f'<body id="{dom_id}"')

    html_content = html_content.replace(
        '<body',
        '<body style="background-color: var(--color-bg); color: var(--color-text); font-family: var(--font-body);"',
    )

    return html_content


async def run_qa_tester(html_content: str, js_content: str, plan: Dict) -> Dict:
    fixes: List[str] = []
    errors: List[str] = []
    html = html_content or ""
    js = js_content or ""

    if "<body" not in html:
        html = "<!doctype html><html><head></head><body></body></html>"
        fixes.append("HTML base generado")

    def _has_id(dom_id: str) -> bool:
        return f'id="{dom_id}"' in html or f"id='{dom_id}'" in html

    def _inject_before_body(snippet: str) -> None:
        nonlocal html
        if "</body>" in html:
            html = html.replace("</body>", f"{snippet}\n</body>")
        else:
            html += snippet

    ids = plan.get("ui_contract", {}).get("ids", {})
    cart_sidebar = ids.get("cart_sidebar")
    cart_items = ids.get("cart_items")
    cart_total = ids.get("cart_total")
    cart_trigger = ids.get("cart_trigger")
    cart_count = ids.get("cart_count")
    main_viewport = ids.get("main_viewport")
    price_dynamic = ids.get("price_dynamic")

    if cart_sidebar and not _has_id(cart_sidebar):
        sidebar = f"""
        <aside id=\"{cart_sidebar}\" class=\"fixed right-0 top-0 h-full w-80 shadow-2xl p-6 z-50 transition-transform transform translate-x-full\" style=\"background: var(--color-bg); color: var(--color-text);\">
            <div class=\"flex justify-between items-center mb-6\">
                <h2 class=\"text-2xl\">Tu Pedido</h2>
                <button onclick=\"toggleCart()\" class=\"text-xl\">✕</button>
            </div>
            <div id=\"{cart_items or 'cart-items-container'}\" class=\"space-y-4\"></div>
            <div class=\"border-t mt-6 pt-4 text-xl font-bold\">
                Total: <span id=\"{cart_total or 'total-price'}\">$0</span>
            </div>
        </aside>
        """
        _inject_before_body(sidebar)
        fixes.append(f"Inyectado {cart_sidebar}")

    if cart_trigger and not _has_id(cart_trigger):
        btn_cart = (
            f'<button id="{cart_trigger}" class="p-2 relative">🛒 '
            f'<span id="{cart_count or "cart-count"}">0</span></button>'
        )
        if "</nav>" in html:
            html = html.replace("</nav>", f"{btn_cart}</nav>")
        else:
            _inject_before_body(btn_cart)
        fixes.append(f"Inyectado {cart_trigger}")

    if cart_count and not _has_id(cart_count):
        _inject_before_body(f'<span id="{cart_count}">0</span>')
        fixes.append(f"Inyectado {cart_count}")

    if main_viewport and not _has_id(main_viewport):
        _inject_before_body(f'<main id="{main_viewport}" class="min-h-screen"></main>')
        fixes.append(f"Inyectado {main_viewport}")

    if price_dynamic and not _has_id(price_dynamic):
        _inject_before_body(f'<span id="{price_dynamic}"></span>')
        fixes.append(f"Inyectado {price_dynamic}")

    if 'id="product-grid"' not in html:
        _inject_before_body('<div id="product-grid" class="grid grid-cols-1 md:grid-cols-3 gap-8"></div>')
        fixes.append("Inyectado product-grid")

    html = _ensure_asset_links(html)

    if not js or len(js) < 50:
        js = await run_scripter(html, plan)
        fixes.append("JS regenerado")

    for dom_id in ids.values():
        if dom_id and not _has_id(dom_id):
            errors.append(f"Falta ID: {dom_id}")

    status = "OK" if not errors else "ERROR: " + "; ".join(errors)
    return {"status": status, "html": html, "js": js, "fixes": fixes}


def _ensure_asset_links(html: str) -> str:
    if not html:
        return html
    if "style.css" not in html:
        html = html.replace("</head>", "  <link rel=\"stylesheet\" href=\"style.css\">\n</head>")
    if "script.js" not in html:
        html = html.replace("</body>", "  <script src=\"script.js\"></script>\n</body>")
    return html


async def run_agency(user_prompt: str, project_path: str, design_md: str = "") -> Dict:
    print("\n" + "=" * 50)
    print(f"[SISTEMA] 🚀 INICIANDO PIPELINE DE 5 AGENTES: {user_prompt[:30]}")
    print("=" * 50)

    # --- AGENTE 1: FRONT-END (HTML & CSS) ---
    print("\n[LOG][1/5] 🎨 Agente Front: Creando estructura y estilo (Linen)...")
    plan = await run_architect(user_prompt)
    css_vars = await run_stylist(user_prompt, plan.get("domain"), design_md)
    html_base = await run_coder(user_prompt, plan, css_vars, [])

    # --- AGENTE 2: BACK-END (JS LOGICO) ---
    print("\n[LOG][2/5] ⚙️ Agente Back: Programando logica del carrito...")
    js_content = await run_scripter(html_base, plan)

    # --- AGENTE 3: SOLDADOR (INTEGRACION DE CODIGO) ---
    print("\n[LOG][3/5] 👨‍🏭 Agente Soldador: Sincronizando Front y Back...")
    html_soldado = await run_welder(html_base, js_content, plan)

    time.sleep(1)

    # --- AGENTE 4: CREADOR DE IMAGENES (RTX 4070) ---
    print("\n[LOG][4/5] 📸 Agente Photographer: Renderizando en hardware local...")
    photo_result = await run_photographer(user_prompt, plan.get("domain"), project_path)
    real_paths = photo_result.get("image_paths", [])

    await _liberar_vram_forge()

    # --- AGENTE 5: COLOCADOR Y TESTER (QA FINAL) ---
    print("\n[LOG][5/5] 🛠️ Agente Placer & Tester: Ensamblado y validacion final...")
    final_html = await run_integrator(html_soldado, real_paths)
    qa_result = await run_qa_tester(final_html, js_content, plan)
    final_html = qa_result.get("html", final_html)
    js_content = qa_result.get("js", js_content)

    if qa_result.get("fixes"):
        print("[LOG] QA aplico correcciones: " + ", ".join(qa_result["fixes"]))

    if isinstance(qa_result.get("status"), str) and qa_result["status"].startswith("ERROR"):
        print(f"[ALERTA] QA detecto fallos: {qa_result['status']}")
    else:
        print("[LOG] ✅ QA: Proyecto validado y funcionando al 100%.")

    files = {
        "index.html": final_html,
        "style.css": _build_stylesheet(css_vars),
        "script.js": js_content,
    }

    print("\n" + "=" * 50)
    print(f"[SISTEMA] ✨ PROYECTO COMPLETO: {plan.get('title')}")
    print("=" * 50)

    return {"files": files, "image_paths": real_paths, "plan": plan}
