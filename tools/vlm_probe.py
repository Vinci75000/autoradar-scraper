import sys, os, json, time, base64, struct, urllib.request
from playwright.sync_api import sync_playwright

URL = sys.argv[1]
LABEL = sys.argv[2] if len(sys.argv) > 2 else "probe"
MODEL = os.environ.get("VLM_MODEL", "qwen2.5vl:7b")
SHOT = "/tmp/vlm_%s.png" % LABEL

CONSENT = ["Alles akzeptieren", "Alle akzeptieren", "Akzeptieren", "Zustimmen",
           "Einverstanden", "Tout accepter", "Accepter", "J'accepte",
           "Accept all", "Accept", "I agree", "Agree", "Got it", "OK"]

PROMPT_DESC = ("Describe in ONE short sentence what this screenshot shows. "
               "If it is blank, white, empty, or a cookie/consent/bot-check wall, say exactly that.")

PROMPT_JSON = (
    "You read a car classified ad screenshot. Return STRICT JSON only, no prose, no fences. "
    'Schema: {"make":str|null,"model":str|null,"year":int|null,"price_eur":int|null,'
    '"mileage_km":int|null,"city":str|null,"country":str|null,"tuner":str|null,'
    '"confidence":0..1}. '
    "Rules: price integer in EUR, no separators. If mileage is in miles, convert to km. "
    "tuner = visible aftermarket house (Carlsson, AMG, Brabus, Alpina, Ruf) else null. "
    "Use null when not visible. Never invent a number."
)

def ollama(prompt, img_b64):
    payload = json.dumps({"model": MODEL, "prompt": prompt, "images": [img_b64],
                          "stream": False, "options": {"temperature": 0}}).encode()
    r = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=payload,
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=900)).get("response", "")

def try_consent(pg):
    for lab in CONSENT:
        try:
            loc = pg.get_by_role("button", name=lab, exact=False).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=3000)
                pg.wait_for_timeout(2500)
                return "button:" + lab
        except Exception:
            pass
    for fr in pg.frames:
        for lab in CONSENT:
            try:
                loc = fr.get_by_role("button", name=lab, exact=False).first
                if loc.count() and loc.is_visible():
                    loc.click(timeout=3000)
                    pg.wait_for_timeout(2500)
                    return "iframe:" + lab
            except Exception:
                pass
    return None

t0 = time.time()
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page()
    try:
        pg.set_viewport_size({"width": 1400, "height": 1500})
    except Exception as e:
        print("viewport non settable (Chrome reel): %r" % (e,))
    pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
    pg.bring_to_front()
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    consent = try_consent(pg)
    pg.mouse.wheel(0, 500); pg.wait_for_timeout(1500)
    pg.mouse.wheel(0, -500); pg.wait_for_timeout(1000)
    title = pg.title()
    try:
        body = " ".join(pg.inner_text("body").split())[:400]
    except Exception:
        body = "(inner_text KO)"
    vp = pg.viewport_size
    shot = pg.screenshot(path=SHOT, full_page=False)
    pg.close()
t_shot = time.time() - t0

try:
    w, h = struct.unpack(">II", shot[16:24])
except Exception:
    w = h = 0
blank = "SUSPECT BLANC" if len(shot) < 40000 else "ok"

print("--- PAGE ---")
print("title   : %s" % title)
print("consent : %s" % consent)
print("viewport: %s" % (vp,))
print("png     : %dx%d  %d bytes  [%s]" % (w, h, len(shot), blank))
print("body    : %s" % body)

img = base64.b64encode(shot).decode()
t1 = time.time(); desc = ollama(PROMPT_DESC, img); t_desc = time.time() - t1
print("--- CONTROLE VISION ---")
print(desc.strip())

t2 = time.time(); raw = ollama(PROMPT_JSON, img); t_json = time.time() - t2
print("--- RAW ---")
print(raw)
print("--- TIMING --- shot %.1fs / desc %.1fs / json %.1fs" % (t_shot, t_desc, t_json))
print("--- SHOT --- %s" % SHOT)
