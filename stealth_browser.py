"""
AutoRadar — Stealth browser v2 (corrigé, sans bug asyncio)
═══════════════════════════════════════════════════════════════
Fichier : ~/Desktop/autoradar-scraper/stealth_browser.py (REMPLACE l'ancien)

Refonte propre du module stealth pour bypasser Cloudflare/DataDome.

Bug v1 corrigé :
- v1 mélangeait playwright_stealth.use_sync() et sync_playwright()
  → conflit asyncio loop systématique
- v2 utilise UNIQUEMENT sync_playwright() avec init_script anti-detection
  → 100% compatible, plus prévisible

Usage :
    from stealth_browser import get_stealth_browser

    with get_stealth_browser('schumachermotors') as (browser, ctx, page):
        page.goto('https://www.schumacher-motors.com/inventory')
        ...
"""

import os
import random
import time
import json
from contextlib import contextmanager
from pathlib import Path

# ─── Sessions persistantes par site ───
SESSIONS_DIR = Path(os.path.expanduser('~/Desktop/autoradar-scraper/.sessions'))
SESSIONS_DIR.mkdir(exist_ok=True)


# ─── User-Agents réalistes Mac/Chrome très récents (mai 2026) ───
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
]

# ─── Locale + timezone par site ───
LOCALE_BY_SITE = {
    # FR
    'classicnumber':  ('fr-FR', 'Europe/Paris'),
    'gotothegrid':    ('fr-FR', 'Europe/Paris'),
    'racemarket':     ('fr-FR', 'Europe/Paris'),
    'plethore':       ('fr-FR', 'Europe/Paris'),
    'carjager':       ('fr-FR', 'Europe/Paris'),
    'lesanciennes':   ('fr-FR', 'Europe/Paris'),
    'lacentrale':     ('fr-FR', 'Europe/Paris'),
    'leboncoin':      ('fr-FR', 'Europe/Paris'),
    'ofa':            ('fr-FR', 'Europe/Paris'),
    'moteuretsens':   ('fr-FR', 'Europe/Paris'),
    'excelcar':       ('fr-FR', 'Europe/Paris'),
    'db7autos':       ('fr-FR', 'Europe/Paris'),
    'eliandre':       ('fr-FR', 'Europe/Paris'),
    'evocars':        ('fr-FR', 'Europe/Paris'),
    'bstore':         ('fr-FR', 'Europe/Paris'),
    'econcession':    ('fr-FR', 'Europe/Paris'),
    # BE
    '2ememain':       ('fr-BE', 'Europe/Brussels'),
    'gocar':          ('fr-BE', 'Europe/Brussels'),
    'autolive':       ('fr-BE', 'Europe/Brussels'),
    'oldtimerfarm':   ('fr-BE', 'Europe/Brussels'),
    'vroom':          ('fr-BE', 'Europe/Brussels'),
    'bavariamotors':  ('fr-BE', 'Europe/Brussels'),
    'kuurnemotors':   ('fr-BE', 'Europe/Brussels'),
    # CH
    'tutti':          ('fr-CH', 'Europe/Zurich'),
    'anibis':         ('fr-CH', 'Europe/Zurich'),
    'car4you':        ('fr-CH', 'Europe/Zurich'),
    'carugati':       ('fr-CH', 'Europe/Zurich'),
    'pereggocars':    ('fr-CH', 'Europe/Zurich'),
    'lambogeneve':    ('fr-CH', 'Europe/Zurich'),
    'lamboporrentruy':('fr-CH', 'Europe/Zurich'),
    'modenacars':     ('fr-CH', 'Europe/Zurich'),
    'rrgeneva':       ('fr-CH', 'Europe/Zurich'),
    # LU
    'luxauto':        ('fr-LU', 'Europe/Luxembourg'),
    'automarket':     ('fr-LU', 'Europe/Luxembourg'),
    'autolu':         ('fr-LU', 'Europe/Luxembourg'),
    'schumachermotors':('fr-LU', 'Europe/Luxembourg'),
    'prestigegt':     ('fr-LU', 'Europe/Luxembourg'),
    'luxsellect':     ('fr-LU', 'Europe/Luxembourg'),
    'dealndrive':     ('fr-LU', 'Europe/Luxembourg'),
    # International
    'classictrader':  ('en-US', 'Europe/Berlin'),
    'classicdriver':  ('en-US', 'Europe/Zurich'),
    'collectingcars': ('en-GB', 'Europe/London'),
    'carandclassic':  ('en-GB', 'Europe/London'),
    'pistonheads':    ('en-GB', 'Europe/London'),
    'mobile':         ('de-DE', 'Europe/Berlin'),
    'kleinanzeigen':  ('de-DE', 'Europe/Berlin'),
    'marktplaats':    ('nl-NL', 'Europe/Amsterdam'),
    'subito':         ('it-IT', 'Europe/Rome'),
    'wallapop':       ('es-ES', 'Europe/Madrid'),
    'willhaben':      ('de-AT', 'Europe/Vienna'),
    'otomoto':        ('pl-PL', 'Europe/Warsaw'),
    'blocket':        ('sv-SE', 'Europe/Stockholm'),
    'dyler':          ('en-US', 'Europe/Berlin'),
    'goodtimers':     ('fr-FR', 'Europe/Paris'),
    'jenden':         ('en-US', 'Europe/Warsaw'),
    'superclassics':  ('en-GB', 'Europe/London'),
}

# ─── Viewports plausibles (machines courantes) ───
VIEWPORTS = [
    {'width': 1366, 'height': 768},
    {'width': 1440, 'height': 900},
    {'width': 1536, 'height': 864},
    {'width': 1920, 'height': 1080},
]


def _get_locale_tz(source: str):
    return LOCALE_BY_SITE.get(source, ('fr-FR', 'Europe/Paris'))


def _session_path(source: str) -> Path:
    return SESSIONS_DIR / f'{source}_session.json'


def human_delay(min_s=1.0, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(page, scrolls=3):
    """Scroll progressif comme un humain qui lit la page."""
    for _ in range(scrolls):
        try:
            page.mouse.wheel(0, random.randint(300, 700))
            time.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass


def human_mouse_jiggle(page):
    """Petit mouvement de souris aléatoire."""
    try:
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        page.mouse.move(x, y, steps=random.randint(5, 15))
    except Exception:
        pass


# ─── Init script anti-detection ───
# Injecté AVANT que le site charge son JS. Masque les signaux Playwright
# que Cloudflare/DataDome utilisent pour détecter les bots.
STEALTH_INIT_JS = """
// Masque navigator.webdriver (le signal n°1 anti-bot)
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// Chrome runtime fictif
window.chrome = window.chrome || { runtime: {}, loadTimes: function() {}, csi: function() {} };

// Plugins fictifs réalistes
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer' },
    ]
});

// Permissions cohérentes
const originalQuery = navigator.permissions && navigator.permissions.query;
if (originalQuery) {
    navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
}

// Languages cohérent
Object.defineProperty(navigator, 'languages', {
    get: () => ['fr-FR', 'fr', 'en-US', 'en']
});

// Hardware concurrency réaliste (valeur Mac courante)
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8
});

// Device memory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8
});

// WebGL vendor (signature classique non-bot)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';        // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
    return getParameter.call(this, parameter);
};
"""


@contextmanager
def get_stealth_browser(source: str, headless: bool = True, save_session: bool = True):
    """
    Context manager qui yield (browser, context, page) configuré stealth.

    CETTE VERSION (v2) UTILISE UNIQUEMENT sync_playwright (pas de package
    playwright_stealth qui causait le bug asyncio).

    Args:
        source: nom de la source (utilisé pour locale + session persistante)
        headless: True pour invisible, False pour debug visuel
        save_session: True pour sauvegarder cookies (réutilisés au prochain run)

    Yields:
        (browser, context, page) tuple
    """
    from playwright.sync_api import sync_playwright

    locale, timezone = _get_locale_tz(source)
    user_agent = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    session_file = _session_path(source)

    pw = sync_playwright().start()
    browser = None
    try:
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-web-security',
            ]
        )

        ctx_args = {
            'user_agent': user_agent,
            'locale': locale,
            'timezone_id': timezone,
            'viewport': viewport,
            'screen': {'width': viewport['width'], 'height': viewport['height']},
            'device_scale_factor': random.choice([1, 2]),
            'has_touch': False,
            'is_mobile': False,
            'java_script_enabled': True,
            'extra_http_headers': {
                'Accept-Language': f'{locale},en-US;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Sec-CH-UA': '"Chromium";v="124", "Google Chrome";v="124", "Not.A/Brand";v="99"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"macOS"',
            },
        }

        # Session persistante si dispo
        if save_session and session_file.exists():
            try:
                ctx_args['storage_state'] = str(session_file)
            except Exception:
                pass

        ctx = browser.new_context(**ctx_args)
        ctx.add_init_script(STEALTH_INIT_JS)

        page = ctx.new_page()

        yield browser, ctx, page

        # Sauvegarde la session
        if save_session:
            try:
                ctx.storage_state(path=str(session_file))
            except Exception:
                pass

    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        try:
            pw.stop()
        except Exception:
            pass


# ─── Test rapide ───
if __name__ == "__main__":
    print(f"Stealth Browser v2 — sessions dans : {SESSIONS_DIR}")
    print(f"Sites configurés : {len(LOCALE_BY_SITE)}")
    print(f"User-Agents : {len(USER_AGENTS)}")
    print(f"Viewports : {len(VIEWPORTS)}")
    print()
    print("Test : ouverture stealth de https://www.schumacher-motors.com/")
    try:
        with get_stealth_browser('schumachermotors', headless=True) as (browser, ctx, page):
            page.goto('https://www.schumacher-motors.com/', timeout=30000)
            human_delay(2, 4)
            title = page.title()
            print(f"✓ Page chargée : '{title}'")
            print(f"✓ URL finale : {page.url}")
            content = page.content()
            if 'cloudflare' in content.lower() or 'just a moment' in content.lower():
                print("⚠️  Cloudflare challenge détecté — proxy résidentiel probablement nécessaire")
            else:
                print("✓ Aucun challenge Cloudflare détecté")
                print(f"✓ HTML reçu : {len(content)} octets")
    except Exception as e:
        print(f"✗ Erreur : {type(e).__name__} : {e}")
