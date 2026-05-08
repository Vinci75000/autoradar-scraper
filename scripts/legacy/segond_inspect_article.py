#!/usr/bin/env python3
"""
Segond — Étape 0.6 : dump structure article fiche.

Le microdata Schema.org Vehicle de Segond est quasi vide (juste 'name').
Il faut identifier les selectors CSS custom WP pour les champs réels :
prix, km, année, BV, carburant, description, puissance.

Ce script :
1. Fetch la fiche Lambo Huracan Sterrato (415 000 € attendus)
2. Vérifie que le prix est rendu serveur (pas JS-only)
3. Sauve l'article isolé en /tmp/segond_article_dump.html (inspection visuelle)
4. Dumpe console :
   - Éléments avec classes CSS matchant mots-clés (prix, km, annee, boite...)
   - Structures <dl>/<dt>/<dd> (key/value typiques des fiches)
   - Structures <table>
   - Contenu détaillé du .bloc-info-prix

Output → permet de choisir les selectors stables pour l'extracteur étape 1.

Usage :
    cd ~/Code/autoradar/scraper
    python -u segond_inspect_article.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

URL = ("https://www.segond-automobiles.com/vehicules/lamborghini/"
       "2003751-lamborghini-huracan-sterrato-5-2-v10-610-4wd-ldf7/")
OUT_HTML = Path("/tmp/segond_article_dump.html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# Mots-clés qu'on cherche dans les classes CSS de l'article
KEYWORDS = [
    "prix", "price",
    "km", "kilom", "mileage",
    "annee", "année", "year", "date", "circulation", "mec",
    "boite", "boîte", "bv", "transmission", "gear",
    "carburant", "energie", "énergie", "fuel",
    "puissance", "power",
    "couleur", "color",
    "description", "desc",
    "caract", "info", "specs", "fiche", "details",
    "bloc",
]


def fetch(url: str, timeout: int = 20) -> Optional[str]:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            print(f"  [{r.status_code}] {url}")
        except requests.RequestException as e:
            print(f"  [err {attempt+1}/3] {e}")
        time.sleep(1.5)
    return None


def short_text(node, maxlen: int = 80) -> str:
    txt = node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node)
    txt = re.sub(r"\s+", " ", txt)
    if len(txt) > maxlen:
        txt = txt[:maxlen] + "…"
    return txt


def main() -> int:
    print("=" * 70)
    print("Segond — Étape 0.6 : dump structure article fiche")
    print("=" * 70)
    print(f"\nURL : {URL}")

    html = fetch(URL)
    if not html:
        print("❌ fetch failed")
        return 1

    # 1. Sanity : prix rendu serveur ?
    print("\n[1] Sanity check rendu serveur")
    if "415 000" in html or "415\u00a0000" in html or "415000" in html:
        print("  ✅ Prix '415 000 €' présent dans HTML brut → rendu serveur")
    else:
        m = re.search(r"\d{2,3}[\s.\u00a0]\d{3}\s*€", html)
        if m:
            print(f"  ✅ Prix '{m.group(0)}' trouvé dans HTML brut → rendu serveur")
        else:
            print("  ⚠️  Aucun pattern prix → possiblement rendu JS, vérifier")

    soup = BeautifulSoup(html, "html.parser")
    article = (
        soup.find("article", class_="nc-fiche-vehicule")
        or soup.find(attrs={"itemtype": re.compile(r"schema\.org/Vehicle", re.I)})
    )
    if not article:
        print("❌ article.nc-fiche-vehicule introuvable")
        return 1
    print(f"  ✅ Article trouvé : {article.name}.{'.'.join(article.get('class') or [])}")

    # 2. Sauve article isolé en HTML (inspection visuelle navigateur)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    minimal = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Segond article dump (sans CSS du site)</title>
<base href="https://www.segond-automobiles.com/">
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 2em auto; padding: 1em; }}
img {{ max-width: 100%; }}
.dump-warning {{ background: #fffbcc; padding: 8px; border-left: 4px solid #d4a017; margin-bottom: 1em; }}
</style>
</head>
<body>
<div class="dump-warning">
  <strong>Dump article isolé Segond.</strong>
  Sans CSS du site, structure brute pour identifier les selectors.
</div>
{article}
</body>
</html>"""
    OUT_HTML.write_text(minimal, encoding="utf-8")
    print(f"\n[2] Article isolé sauvé : {OUT_HTML}")
    print(f"    Ouvre avec : open {OUT_HTML}")

    # 3. Dump éléments avec classes matchant mots-clés
    print("\n" + "─" * 70)
    print("[3] ÉLÉMENTS AVEC CLASSES CSS MATCHANT MOTS-CLÉS")
    print("─" * 70)
    seen_signatures: set = set()
    matches = 0
    for el in article.find_all(class_=True):
        classes = el.get("class") or []
        if not any(any(kw in c.lower() for kw in KEYWORDS) for c in classes):
            continue
        sig = (el.name, tuple(sorted(classes)))
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        matches += 1
        txt = short_text(el, 120)
        cls_str = ".".join(classes[:4])
        print(f"\n  <{el.name}.{cls_str}>")
        print(f"     → {txt}")
    if not matches:
        print("  (aucun élément matche)")

    # 4. Structures <dl>/<dt>/<dd>
    print("\n" + "─" * 70)
    print("[4] STRUCTURES <dl>/<dt>/<dd> (key/value)")
    print("─" * 70)
    dls = article.find_all("dl")
    if dls:
        for i, dl in enumerate(dls, 1):
            cls = ".".join(dl.get("class") or [])
            print(f"\n  <dl{('.' + cls) if cls else ''}> #{i}")
            for dt in dl.find_all("dt"):
                key = short_text(dt, 50)
                dd = dt.find_next_sibling("dd")
                val = short_text(dd, 100) if dd else "(no dd)"
                print(f"    {key:30s} → {val}")
    else:
        print("  (aucun <dl>)")

    # 5. Structures <table>
    print("\n" + "─" * 70)
    print("[5] STRUCTURES <table>")
    print("─" * 70)
    tables = article.find_all("table")
    if tables:
        for i, t in enumerate(tables, 1):
            cls = ".".join(t.get("class") or [])
            print(f"\n  <table{('.' + cls) if cls else ''}> #{i}")
            for tr in t.find_all("tr"):
                cells = [short_text(c, 80) for c in tr.find_all(["th", "td"])]
                if cells:
                    print(f"    {' | '.join(cells)}")
    else:
        print("  (aucune <table>)")

    # 6. <ul>/<li> dans zones probables (caractéristiques)
    print("\n" + "─" * 70)
    print("[6] STRUCTURES <ul>/<li> dans zones 'caract'/'info'/'specs'")
    print("─" * 70)
    info_zones = article.select(
        "[class*=caract], [class*=info], [class*=specs], [class*=details], [class*=fiche]"
    )
    li_seen: set = set()
    for zone in info_zones:
        for ul in zone.find_all("ul"):
            cls = ".".join(ul.get("class") or [])
            sig = (cls, len(ul.find_all("li")))
            if sig in li_seen:
                continue
            li_seen.add(sig)
            print(f"\n  <ul{('.' + cls) if cls else ''}> ({len(ul.find_all('li'))} items)")
            for li in ul.find_all("li", recursive=False)[:8]:
                print(f"    · {short_text(li, 100)}")

    # 7. Bloc prix détaillé
    print("\n" + "─" * 70)
    print("[7] BLOC .bloc-info-prix (structure DOM)")
    print("─" * 70)
    bp = (
        article.select_one(".bloc-info-prix")
        or article.select_one("[class*=info-prix]")
        or article.select_one("[class*=prix]")
    )
    if bp:
        def render(node, depth: int = 0) -> None:
            indent = "  " * depth
            if isinstance(node, NavigableString):
                txt = str(node).strip()
                if txt:
                    print(f"{indent}TEXT: {txt[:120]}")
                return
            if not isinstance(node, Tag):
                return
            classes = ".".join(node.get("class") or [])
            cls = f".{classes}" if classes else ""
            el_id = node.get("id")
            id_str = f"#{el_id}" if el_id else ""
            print(f"{indent}<{node.name}{id_str}{cls}>")
            for c in node.children:
                render(c, depth + 1)

        render(bp)
    else:
        print("  (pas de bloc prix trouvé via les selectors testés)")

    print("\n" + "=" * 70)
    print("À partir de ce dump on identifie les selectors stables pour :")
    print("  prix, km, année, BV, carburant, description, puissance")
    print("Puis étape 1 = extracteur custom_segond.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
