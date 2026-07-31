#!/usr/bin/env python3
"""Dump images + candidats galerie sur une annonce KA. Lecture seule."""
import sys, os, re, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from playwright.sync_api import sync_playwright
import refresh_listings as RL

tg = RL.load_targets("Kleinanzeigen.de", 1, only_no_photos=True)
if not tg:
    print("aucune cible"); sys.exit(1)
url = tg[0]["src_url"]
print("URL :", url)

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(2500)

    print("\n=== 1. HOSTS DES IMAGES ===")
    hosts = pg.evaluate("""() => {
      const h = {};
      document.querySelectorAll('img').forEach(i => {
        const s = i.currentSrc || i.src || i.getAttribute('data-src') || '';
        if (!s) return;
        try { const u = new URL(s, location.href); h[u.host] = (h[u.host]||0)+1; } catch(e){}
      });
      return h;
    }""")
    for k, v in sorted(hosts.items(), key=lambda x: -x[1]):
        print("  %-40s x%d" % (k, v))

    print("\n=== 2. ECHANTILLON URLS IMAGES ===")
    for u in pg.evaluate("""() => [...document.querySelectorAll('img')]
        .map(i => i.currentSrc || i.src || i.getAttribute('data-src') || '')
        .filter(Boolean).slice(0, 14)"""):
        print("  " + u[:150])

    print("\n=== 3. CANDIDATS GALERIE (classes/ids) ===")
    for s in pg.evaluate("""() => {
      const out = [];
      document.querySelectorAll('[class*="gallery"],[class*="galerie"],[id*="gallery"],[class*="slider"],[class*="carousel"],[class*="thumb"],[data-imgindex],[class*="viewad-image"]')
        .forEach(e => out.push(e.tagName.toLowerCase() + '.' + (e.className||'').toString().slice(0,70) + ' #' + (e.id||'')));
      return [...new Set(out)].slice(0, 25);
    }"""):
        print("  " + s)

    print("\n=== 4. COMPTEUR ANNONCE (n/total) ===")
    print("  " + str(pg.evaluate("""() => {
      const t = document.body.innerText.match(/\\b\\d+\\s*\\/\\s*\\d+\\b/g);
      return t ? t.slice(0,5) : 'aucun';
    }""")))

    print("\n=== 5. JSON EMBARQUE (recherche urls images) ===")
    n = pg.evaluate("""() => {
      let best = 0;
      document.querySelectorAll('script').forEach(s => {
        const t = s.textContent || '';
        const m = t.match(/https?:\\/\\/[^"']*prod-ads[^"']*/g);
        if (m && m.length > best) best = m.length;
      });
      return best;
    }""")
    print("  urls 'prod-ads' dans les <script> : %d" % n)
    pg.close()
