"""
scrape_cc_resident.py — Car & Classic, profil Chromium PERSISTANT (passe Cloudflare
via ta session connectée), sur TON Mac.

POURQUOI
────────
carandclassic met un Cloudflare que rien d'automatisé nu ne passe. Mais TON Chrome
connecté passe. On reproduit ça : un profil Chromium persistant où tu te connectes
UNE fois → ensuite headless pour toujours, il reste connecté et franchit Cloudflare.

FLOT
────
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  # 1) une seule fois : ouvre une fenêtre, tu te connectes à carandclassic (+ cookies) :
  python3 scrape_cc_resident.py --login
  # 2) découverte : dump la structure des cartes (pour finaliser le parser) :
  python3 scrape_cc_resident.py --dump
  # 3) (plus tard) insertion incrémentale :
  python3 scrape_cc_resident.py --apply

Le profil vit dans .sessions/cc_profile/ (git-ignore-le).
"""
import argparse, json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
from playwright.sync_api import sync_playwright
try:
    from stealth_browser import STEALTH_INIT_JS
except Exception:
    STEALTH_INIT_JS = ""

PROFILE = Path(__file__).resolve().parent / ".sessions" / "cc_profile"
PROFILE.mkdir(parents=True, exist_ok=True)
# recherche triée par plus récentes (ajuste le filtre à ta guise)
SEARCH_URL = "https://www.carandclassic.com/search?category=1&sort=newest"

def launch(pw, headless):
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE), headless=headless, locale="fr-FR",
        viewport={"width":1440,"height":900},
        args=["--disable-blink-features=AutomationControlled","--no-sandbox"])
    if STEALTH_INIT_JS:
        try: ctx.add_init_script(STEALTH_INIT_JS)
        except Exception: pass
    return ctx

def collect_cards(page, scrolls=25):
    """Scroll (virtual list) en collectant les cartes /car/C{id} au fur et à mesure."""
    seen = {}
    for _ in range(scrolls):
        rows = page.evaluate("""() => {
          const out=[];
          for (const a of document.querySelectorAll('a[href*="/car/C"]')) {
            const id=(a.getAttribute('href').match(/C\\d+/)||[])[0]; if(!id) continue;
            const card=a.closest('article,li,[class*="card"]')||a.parentElement;
            out.push({id, href:a.getAttribute('href'), text:(card?card.innerText:a.innerText).replace(/\\s+/g,' ').trim()});
          }
          return out;
        }""")
        for r in rows:
            if r["id"] not in seen: seen[r["id"]] = r
        page.evaluate("window.scrollBy(0, document.body.scrollHeight*0.8)")
        page.wait_for_timeout(700)
    return list(seen.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="ouvre une fenêtre pour te connecter une fois")
    ap.add_argument("--dump", action="store_true", help="dump la structure des cartes (finaliser le parser)")
    ap.add_argument("--apply", action="store_true", help="(après finalisation) insère en base")
    ap.add_argument("--url", default=SEARCH_URL)
    ap.add_argument("--scrolls", type=int, default=25)
    a = ap.parse_args()

    with sync_playwright() as pw:
        if a.login:
            ctx = launch(pw, headless=False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.carandclassic.com/account/login", wait_until="domcontentloaded")
            print(">> Connecte-toi dans la fenêtre (résous Cloudflare si besoin).")
            print(">> Quand tu es connecté et que tu vois ton compte, reviens ici et appuie sur Entrée.")
            try: input()
            except EOFError: time.sleep(60)
            ctx.close(); print(">> Profil sauvegardé dans .sessions/cc_profile/"); return

        ctx = launch(pw, headless=not a.dump)  # --dump visible pour voir ce qui se passe
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(a.url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3500)
        low = page.content().lower()
        if any(k in low for k in ["just a moment","cf-chl","attention required","checking your browser"]):
            print(">> Cloudflare bloque — relance --login pour rafraîchir la session."); ctx.close(); return
        cards = collect_cards(page, a.scrolls)
        print(f">> cartes collectées: {len(cards)}")
        if a.dump:
            for c in cards[:8]:
                print("―"*70); print(c["id"], c["href"]); print(c["text"][:220])
            Path("/tmp/cc_cards.json").write_text(json.dumps(cards[:40], ensure_ascii=False, indent=1))
            print("\n>> échantillon écrit dans /tmp/cc_cards.json — envoie-le moi pour finaliser le parser.")
        ctx.close()

if __name__ == "__main__":
    main()
