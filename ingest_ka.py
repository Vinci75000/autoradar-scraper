"""
ingest_ka.py — ingère le JSON capturé par le bookmarklet Kleinanzeigen.

Kleinanzeigen = annonces de particuliers, texte libre allemand. Le bookmarklet
capture les cartes (.aditem) de ta recherche → ka_dump.json. Ce script parse
prix / km / année (EZ MM/AAAA) / marque+modèle (dico normalisé vers le registry)
et insère via scraper.insert_car.

USAGE (Mac, venv)
─────────────────
  python3 ingest_ka.py                                   # dry, ~/Downloads/ka_dump.json
  python3 ingest_ka.py --apply
  python3 ingest_ka.py --apply --file ~/Downloads/"ka_dump.json"
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
import scraper

# marques (motif de détection -> nom normalisé registry). Ordre = priorité (longs d'abord).
BRANDS = [
    (r"mercedes[- ]?benz|mercedes|\bmb\b", "Mercedes-Benz"),
    (r"volkswagen|\bvw\b", "Volkswagen"),
    (r"alfa[- ]?romeo", "Alfa Romeo"),
    (r"land[- ]?rover", "Land Rover"),
    (r"range[- ]?rover", "Land Rover"),
    (r"rolls[- ]?royce", "Rolls-Royce"),
    (r"aston[- ]?martin", "Aston Martin"),
    (r"austin[- ]?healey", "Austin-Healey"),
    (r"bmw", "BMW"), (r"audi", "Audi"), (r"porsche", "Porsche"), (r"opel", "Opel"),
    (r"ford", "Ford"), (r"toyota", "Toyota"), (r"nissan", "Nissan"), (r"datsun", "Datsun"),
    (r"honda", "Honda"), (r"mazda", "Mazda"), (r"jaguar", "Jaguar"), (r"bentley", "Bentley"),
    (r"ferrari", "Ferrari"), (r"lamborghini", "Lamborghini"), (r"maserati", "Maserati"),
    (r"lancia", "Lancia"), (r"fiat", "Fiat"), (r"abarth", "Abarth"), (r"citro[eë]n", "Citroën"),
    (r"peugeot", "Peugeot"), (r"renault", "Renault"), (r"alpine", "Alpine"), (r"lotus", "Lotus"),
    (r"triumph", "Triumph"), (r"\bmg\b", "MG"), (r"mini", "Mini"), (r"morgan", "Morgan"),
    (r"volvo", "Volvo"), (r"saab", "Saab"), (r"skoda|škoda", "Skoda"), (r"seat", "Seat"),
    (r"chevrolet", "Chevrolet"), (r"cadillac", "Cadillac"), (r"dodge", "Dodge"),
    (r"chrysler", "Chrysler"), (r"pontiac", "Pontiac"), (r"buick", "Buick"),
    (r"mercury", "Mercury"), (r"oldsmobile", "Oldsmobile"), (r"corvette", "Chevrolet"),
    (r"mustang", "Ford"), (r"jeep", "Jeep"), (r"smart", "Smart"), (r"daimler", "Daimler"),
    (r"morris", "Morris"), (r"rover", "Rover"), (r"de tomaso", "De Tomaso"), (r"tvr", "TVR"),
]

def parse_make(title):
    low = title.lower()
    for pat, norm in BRANDS:
        m = re.search(r"(?<![a-z])(" + pat + r")(?![a-z])", low)
        if m:
            # modèle = titre sans le token marque
            mo = re.sub(r"(?i)(?<![a-z])(" + pat + r")(?![a-z])", "", title, count=1)
            mo = re.sub(r"\s{2,}", " ", mo).strip(" -–,•|") 
            return norm, (mo or norm)
    return None, None

def to_car(c):
    title = (c.get("title") or "").strip()
    text = (c.get("text") or "")
    if not title: title = text
    make, mo = parse_make(title)
    if not make:
        return None
    ym = re.search(r"EZ\s*\d{1,2}/(\d{4})", text) or re.search(r"\b(19|20)\d\d\b", title)
    yr = int(ym.group(1) if ym.lastindex else ym.group(0)) if ym else None
    if not yr or yr < 1900 or yr > datetime.now().year:
        return None
    pm = re.search(r"([\d.]+)\s*€", text)
    px = int(pm.group(1).replace(".", "")) if pm else None
    if px is not None and px < 500: px = None
    km_m = re.search(r"([\d.]+)\s*km", text)
    km = int(km_m.group(1).replace(".", "")) if km_m else None
    if km is not None and (km < 0 or km > 500000): km = None
    fu = "Diesel" if re.search(r"diesel|tdi|hdi|cdi|dci", text, re.I) else \
         ("Électrique" if re.search(r"elektro|\bev\b|electric", text, re.I) else
          ("Hybride" if re.search(r"hybrid", text, re.I) else "Essence"))
    ge = "Automatique" if re.search(r"automat|\bdsg\b|\bat\b|tiptronic", text, re.I) else "Manuelle"
    # lieu : "PLZ Ort" en tête de la carte
    loc = re.search(r"\b(\d{5})\s+([A-ZÄÖÜ][\wäöüß.\- ]+?)(?:\s{2,}|$)", text)
    ci = (loc.group(2).strip() if loc else "Allemagne")[:40]
    url = c.get("url") or ""
    if url.startswith("/"): url = "https://www.kleinanzeigen.de" + url
    if not url: return None
    return scraper.CarListing(
        mk=make, mod=mo, mo=mo, yr=yr, km=km, px=px, fu=fu, ge=ge,
        ci=ci, co="de", src="Kleinanzeigen.de", src_url=url,
        photos=[], age_label=scraper._age_label(datetime.now()), ow=1, opts=[], de="",
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(Path.home() / "Downloads" / "ka_dump.json"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    p = Path(a.file).expanduser()
    if not p.exists():
        print(f">> introuvable: {p}  (clique le bookmarklet Kleinanzeigen d'abord)"); return
    items = json.loads(p.read_text())
    print(f">> {len(items)} cartes dans {p.name}  |  apply={a.apply}", flush=True)
    db = scraper.get_db() if a.apply else None
    ins=dup=rej=skip=0
    for c in items:
        car = to_car(c)
        if not car: skip += 1; continue
        if not a.apply: continue
        out = scraper.insert_car(db, car)
        if out == "rejected": rej += 1
        elif out: ins += 1
        else: dup += 1
    if a.apply: print(f">> insérés={ins} refresh/dup={dup} rejetés={rej} ignorés(map)={skip}")
    else: print(f">> mappables={len(items)-skip} ignorés(pas marque/année/url)={skip} — relance avec --apply")

if __name__ == "__main__":
    main()
