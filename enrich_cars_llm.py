#!/usr/bin/env python3
"""
enrich_cars_llm.py — LLM pass (Ollama local) sur le residuel premium de cars.

Cible UNIQUEMENT les annonces premium/sport encore NULL (ref_match_conf='none'
chez marques premium) que le matching par regles n'a pas couvertes (Audi R8/RS/S,
Jaguar V12, nouveaux modeles...).

Le LLM classe la MOTORISATION seulement (engine_layout, engine_cyl, is_performance).
origin est deja rempli par la marque. Sortie JSON stricte, validee, sinon ignoree.

Modele : qwen2.5-coder:7b (rapide). Fallback deepseek-coder-v2:16b si besoin.

Usage:
    python -u enrich_cars_llm.py --dry --limit 20       # tester le prompt sur 20
    python -u enrich_cars_llm.py --limit 100            # 100 reelles
    python -u enrich_cars_llm.py                        # tout le residuel premium
    python -u enrich_cars_llm.py --model deepseek-coder-v2:16b
"""
import os, sys, re, json, argparse, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from scraper import get_db

try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:7b"

PREMIUM_MK = ['ferrari','porsche','lamborghini','aston','mclaren','maserati','audi',
'bmw','mercedes','jaguar','bentley','alfa','lotus','nissan','toyota','honda','mazda',
'mitsubishi','subaru','alpine','lancia','bugatti','pagani','koenigsegg','rolls']

VALID_LAYOUTS = {'V12','V10','V8','V6','flat6','flat4','L6','L4','L5','L3','rotary','W12','W16','electric','hybrid'}
LAYOUT_CYL = {'V12':12,'V10':10,'V8':8,'V6':6,'flat6':6,'flat4':4,'L6':6,'L4':4,'L5':5,'L3':3,'rotary':2,'W12':12,'W16':16,'electric':0,'hybrid':0}

PROMPT = """You are a precise automotive database. Given brand + listing title, output engine config.

Brand: {mk}
Title: {mo}

Output ONLY JSON, nothing else:
{{"engine_layout": "<V12|V10|V8|V6|flat6|flat4|L6|L4|L5|L3|rotary|W12|W16|electric|hybrid|unknown>", "is_performance": <true|false>}}

ENGINE rules (be conservative, use 'unknown' if not certain):
- Porsche: 911=flat6, 718/Boxster/Cayman 4cyl=flat4, Cayenne/Panamera/Macan=V6 or V8, Taycan=electric
- Audi: R8=V10, RS6/RS7/S6/S7/S8/SQ7/SQ8=V8, RS4/RS5/S4/S5/SQ5=V6, RS3/TTRS=L5, S1/S3=L4
- BMW: M3/M4=L6, M5/M6/M8 modern=V8, 650i/550i/750i=V8, base models=unknown
- Jaguar: E-Type 6cyl=L6, E-Type V12=V12, F-Type=V6 or V8
- Diesel cars (TDI/d/HDi/dCi/D-4D/CDI): almost always L4 or L6, NEVER V8/V10/V12. SUV diesels=L4 or V6.
- If just a base trim with no engine hint (A3, Q5, Golf, Silver Spur): unknown

PERFORMANCE rules (strict):
- TRUE only for genuine sports/GT cars: M/RS/AMG/GT/Type-R/STI/Evo/sports coupes/supercars
- FALSE for: regular sedans, SUVs, diesels, "quattro"/"S tronic"/"4Matic" alone (those are just options, NOT sport)
- A diesel SUV like "Q5 TDI quattro" is FALSE. "Land Cruiser D-4D" is FALSE.
- Audi "S" line (S3/S4/S5/S6) = TRUE, but "S tronic"/"S line" alone = NOT sport (it is a trim)

JSON:"""

def ask_llm(model, mk, mo, timeout=30):
    payload = {
        "model": model,
        "prompt": PROMPT.format(mk=mk, mo=mo),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 80}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        txt = r.json().get('response', '').strip()
        data = json.loads(txt)
        layout = str(data.get('engine_layout', '')).strip()
        perf = data.get('is_performance', None)
        if layout == 'unknown' or layout not in VALID_LAYOUTS:
            layout = None
        if not isinstance(perf, bool):
            perf = None
        # Garde-fou diesel : jamais V8/V10/V12 sur un diesel evident
        mo_l = (mo or '').lower()
        is_diesel = bool(re.search(r'\b(tdi|hdi|dci|cdi|d-4d|d4d|bluetec|bluehdi|diesel|\d\.\d\s*d\b)\b', mo_l))
        if is_diesel and layout in ('V8','V10','V12','W12','W16'):
            layout = None  # hallucination probable
        if is_diesel and perf is True and not re.search(r'\b(m\d|rs\d|amg|sport\s*diff)\b', mo_l):
            perf = False  # diesel non-sport
        return layout, perf
    except Exception as e:
        return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='Limiter le nombre (0=tout)')
    ap.add_argument('--mk', help='Une seule marque')
    args = ap.parse_args()

    db = get_db()
    # Charger le residuel premium NULL
    cars = []
    off = 0
    prem = [args.mk] if args.mk else PREMIUM_MK
    while True:
        q = db.table('cars').select('id,mk,mo').eq('status','active').eq('ref_match_conf','none')
        # filtre premium via OR ilike
        ors = ','.join(f"mk.ilike.%{m}%" for m in prem)
        q = q.or_(ors).order('id').range(off, off+998)
        res = q.execute()
        batch = res.data or []
        cars.extend(batch)
        if len(batch) < 999: break
        off += 999
        if args.limit and len(cars) >= args.limit: break
    if args.limit: cars = cars[:args.limit]
    print(f"Residuel premium a traiter : {len(cars)} (modele: {args.model})")

    done = 0; classified = 0; perf_count = 0
    layouts = {}
    t0 = time.time()
    for i, c in enumerate(cars):
        layout, perf = ask_llm(args.model, c.get('mk',''), c.get('mo',''))
        if args.dry:
            if i < 25:
                print(f"  {str(c.get('mk'))[:12]:12s} {str(c.get('mo'))[:40]:40s} -> {layout or 'unknown':8s} perf={perf}")
            if layout: classified += 1
            continue
        patch = {'ref_match_conf': 'llm'}
        if layout:
            patch['engine_layout'] = layout
            patch['engine_cyl'] = LAYOUT_CYL.get(layout)
            classified += 1
            layouts[layout] = layouts.get(layout,0)+1
        if isinstance(perf, bool):
            patch['is_performance'] = perf
            if perf: perf_count += 1
        try:
            db.table('cars').update(patch).eq('id', c['id']).execute()
        except Exception as e:
            time.sleep(1.0); db = get_db()
            db.table('cars').update(patch).eq('id', c['id']).execute()
        done += 1
        if done % 50 == 0:
            rate = done/(time.time()-t0)
            eta = (len(cars)-done)/rate/60 if rate>0 else 0
            print(f"  ...{done}/{len(cars)} ({classified} classes) {rate:.1f}/s ETA {eta:.0f}min")

    dt = time.time()-t0
    print(f"\n{'[DRY] ' if args.dry else ''}Termine en {dt/60:.1f}min. {len(cars)} traites, {classified} avec layout.")
    if layouts:
        print("Layouts LLM :")
        for lay,n in sorted(layouts.items(), key=lambda x:-x[1]):
            print(f"  {lay:10s} {n}")

if __name__ == '__main__':
    main()
