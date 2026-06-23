#!/usr/bin/env python3
"""
enrich_models_rules.py — Remplissage par REGLES de models_canonical.

Peuple, sans LLM, les colonnes deterministes :
  - is_performance, is_special_edition, is_competition, is_limited, is_icon
  - engine_layout, engine_cyl (pour modeles connus premium)
  - model_family (regroupement trims -> modele parent)
  - era (derive de yr_start)
  - enrich_source='rules', enrich_at=now

Idempotent : recalcule a chaque run, n'ecrase QUE les colonnes regles
(ne touche pas aux colonnes LLM/manual posees ailleurs si enrich_source dit autre chose).

Usage:
    python -u enrich_models_rules.py            # tout le referentiel
    python -u enrich_models_rules.py --mk Ferrari   # une marque
    python -u enrich_models_rules.py --dry         # simulation, aucune ecriture
"""
import os, sys, re, argparse, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from scraper import get_db

# ── REGLES MOTORISATION (modeles premium connus, mo -> layout/cyl) ──────────
# Cle = (mk, pattern regex sur mo lower). Premier match gagne.
ENGINE_RULES = [
    # FERRARI V12
    ('Ferrari', r'\b(testarossa|512\s*tr|512\s*m|550|575|599|612|812|f12|812|365|400|412|456|550|575|daytona|550\s*maranello|550\s*barchetta|575\s*m|575m|599\s*gtb|599\s*gto|f12\s*berlinetta|f12tdf|812\s*superfast|812\s*gts|812\s*competizione|12\s*cilindri|12cilindri|fxx|laferrari|enzo|f50|f40|288\s*gto|250|275|330|342|365)', 'V12', 12),
    # FERRARI V8
    ('Ferrari', r'\b(308|328|348|355|360|430|458|488|296|f8|roma|portofino|california|mondial|gtc4|ff|f355|f430|458\s*italia|488\s*gtb|488\s*pista|f8\s*tributo|sf90|296\s*gtb)', 'V8', 8),
    # LAMBORGHINI V12
    ('Lamborghini', r'\b(countach|diablo|murcielago|aventador|reventon|veneno|centenario|sian|revuelto|miura|espada|jarama|islero|400\s*gt|350\s*gt|lm002|essenza|sesto\s*elemento)', 'V12', 12),
    # LAMBORGHINI V10
    ('Lamborghini', r'\b(gallardo|huracan|huracán)', 'V10', 10),
    # LAMBORGHINI V8 (anciennes + Urus)
    ('Lamborghini', r'\b(urraco|silhouette|jalpa|urus)', 'V8', 8),
    # PORSCHE flat-6 (911 + derives) / flat-4 (718 4cyl) / V8 (Cayenne/Panamera)
    ('Porsche', r'\b(911|912|930|964|993|996|997|991|992|901|carrera\s*gt|959|935|934|906|908|910|718\s*spyder|718\s*cayman\s*gt4|cayman\s*gt4|boxster\s*spyder)', 'flat6', 6),
    ('Porsche', r'\b(718|cayman|boxster|914|924|944|968|982)', 'flat4', 4),
    ('Porsche', r'\b(cayenne|panamera|macan)', 'V6', 6),
    # MASERATI V8 / V6
    ('Maserati', r'\b(granturismo|gransport|quattroporte|coupe|spyder|3200|4200|gt|shamal|ghibli\s*cup|bora|khamsin|kyalami|mexico)', 'V8', 8),
    ('Maserati', r'\b(ghibli|levante|grecale|biturbo|222|228|425|430)', 'V6', 6),
    # ASTON MARTIN V12 / V8
    ('Aston Martin', r'\b(db9|db11|dbs|db12|vanquish|virage|one-77|valkyrie|v12\s*vantage|rapide|db7\s*vantage|valour)', 'V12', 12),
    ('Aston Martin', r'\b(v8\s*vantage|vantage|db7|dbx|db5|db6|db4|vantage\s*gt)', 'V8', 8),
    # BMW M : L6 (S38/S50/S54/S58) ou V8 (E60 M5 S85=V10, E9x M3 S65=V8)
    ('BMW', r'\bm5\b.*\b(e60|e61|v10)\b|\bm6\b.*\b(e63|e64|v10)\b', 'V10', 10),
    ('BMW', r'\bm3\b.*\b(e90|e92|e93|v8|s65)\b', 'V8', 8),
    ('BMW', r'\b(m1|m2|m3|m4|m5|m6|m8|1m|m\s*coupe|m\s*roadster|z3\s*m|z4\s*m)\b', 'L6', 6),
    # MERCEDES AMG V8 / V12
    ('Mercedes-Benz', r'\b(s\s*65|sl\s*65|cl\s*65|g\s*65|s65|sl65|cl65|amg\s*gt\s*black|sls.*black|65\s*amg)', 'V12', 12),
    ('Mercedes-Benz', r'\b(c\s*63|e\s*63|s\s*63|cls\s*63|gt\s*63|sl\s*63|g\s*63|ml\s*63|gle\s*63|c63|e63|s63|sls|amg\s*gt|63\s*amg|clk\s*63|clk\s*55|c\s*55|e\s*55|55\s*amg)', 'V8', 8),
    # ALFA ROMEO
    ('Alfa Romeo', r'\b(8c|montreal|33\s*stradale|tipo\s*33)', 'V8', 8),
    ('Alfa Romeo', r'\b(giulia\s*quadrifoglio|stelvio\s*quadrifoglio|gtv6|164|166|spider\s*v6|gtv\s*v6)', 'V6', 6),
    ('Alfa Romeo', r'\b(4c|giulietta|mito|giulia|spider|gtv|brera|159|156|147|gt)', 'L4', 4),
    # MCLAREN V8
    ('McLaren', r'\b(720|650|570|600|620|650s|675|720s|765|artura|gt|540|p1|senna|elva|speedtail|mp4|f1\b)', 'V8', 8),
    # NISSAN / TOYOTA / HONDA / MAZDA / MITSUBISHI / SUBARU (JDM)
    ('Nissan', r'\b(gt-r|gtr|skyline|r32|r33|r34|r35|350z|370z|z\b|fairlady)', 'V6', 6),
    ('Toyota', r'\b(supra|gr\s*supra|2000gt)', 'L6', 6),
    ('Toyota', r'\b(gt86|86|gr86|mr2|celica|gr\s*yaris|gr\s*corolla)', 'L4', 4),
    ('Honda', r'\b(nsx)', 'V6', 6),
    ('Honda', r'\b(s2000|civic\s*type\s*r|integra|type\s*r)', 'L4', 4),
    ('Acura', r'\b(nsx)', 'V6', 6),
    ('Mazda', r'\b(rx-7|rx7|rx-8|rx8)', 'rotary', 2),
    ('Mazda', r'\b(mx-5|miata|mx5)', 'L4', 4),
    ('Mitsubishi', r'\b(lancer\s*evo|evo|evolution|3000gt|gto)', 'L4', 4),
    ('Subaru', r'\b(impreza|wrx|sti)', 'flat4', 4),
]

# ── PERFORMANCE PAT (versions sport "permanentes" : S/RS Audi, AMG, M, GTI, R) ─
# Large : attrape les designations sport par lettre/prefixe sans les berlines normales.
PERF_PAT = re.compile(r'\b(rs\s?\d?|s[1-8]\b|sq[1-8]|tts|tt\s*rs|gti|gtd|golf\s*r|polo\s*r|\br\b(?!\s*line)|\d{2}\s*amg|amg|quadrifoglio|\bqv\b|abarth|type\s*r|sti|evo|nismo|gt[1-4rs]?|gts|\bcs\b|csl|black\s*series|performante|speciale|scuderia|trofeo|competizione|pista|cup|clubsport|cupra|\bn\b(?!\s)|fiorano|superveloce|sv\b|svj|brabus|alpina|hennessey|mansory|akrapovic|\bturbo\s*s?\b|\bquattro\b)\b', re.I)
# AMG "lettre+nombre" Mercedes (C43, E53, A45, GLC63...) — pattern dedie
AMG_NUM_PAT = re.compile(r'\b([a-z]{1,3})\s*(35|43|45|50|53|55|63|65)\b', re.I)

# ── SPECIAL EDITION (sportive haut de gamme / serie speciale) ───────────────
SPECIAL_PAT = re.compile(r'\b(rs\d?|gt3|gt2|gt4|gtr|gt-r|sti|evo|evolution|type\s*r|black\s*series|scuderia|speciale|performante|trofeo|stradale|sv\b|svj|superveloce|competizione|pista|tributo|cup|club\s*sport|clubsport|nismo|nurburgring|n\s*ring|track|r-line\s*track|quadrifoglio|qv\b|abarth|brabus|alpina|amg|m\s*sport|s\s*line|gts|gt\s*s|49\s*heritage|spirit\s*70|rocket)\b', re.I)

# ── COMPETITION (course / homologation / monoplace) ─────────────────────────
COMPETITION_PAT = re.compile(r'\b(f1|formula\s*1|formula\s*one|f2|f3|gt3|gt2|lmp|lmh|hypercar|le\s*mans|group\s*[abc5]|gr\.\s*[abc5]|dtm|rally\s*car|race\s*car|works|fia\s*gt|homologation|rsr|race-spec|n-gt|gte|imsa|trans-am|nascar|indycar|can-am|tipo\s*33|126\s*c|156\s*f1|248\s*f1|158\s*f1|625\s*f1|312\s*[ptb])\b', re.I)

# ── LIMITED / ICON (collection majeure) ─────────────────────────────────────
LIMITED_PAT = re.compile(r'\b(limited|numbered|one-77|one\s*off|1\s*of\s*\d|edition|anniversary|jubilee|jubilaum|special\s*edition|\d+\s*exemplaires|collector)\b', re.I)
ICON_MODELS = {  # (mk, model_family) pieces majeures de collection
    ('Ferrari','250'),('Ferrari','288'),('Ferrari','F40'),('Ferrari','F50'),('Ferrari','Enzo'),('Ferrari','LaFerrari'),('Ferrari','Daytona'),('Ferrari','Testarossa'),
    ('Lamborghini','Miura'),('Lamborghini','Countach'),('Porsche','Carrera GT'),('Porsche','959'),('Porsche','911'),
    ('Mercedes-Benz','300 SL'),('Jaguar','E-Type'),('Aston Martin','DB5'),('McLaren','F1'),('Bugatti','Type 35'),
}

# ── MARQUES 100% PERFORMANCE (toute la gamme est sportive) ──────────────────
ALL_PERFORMANCE_MK = {'Ferrari','Lamborghini','McLaren','Pagani','Koenigsegg','Bugatti','Lotus','Alpine','Caterham','Noble','TVR','Gumpert','Wiesmann','Donkervoort','Ariel','Radical','BAC','Hennessey','Saleen','SSC','Vector'}

# ── ERA depuis yr_start ─────────────────────────────────────────────────────
def derive_era(yr_start):
    if not yr_start: return None
    if yr_start < 1945: return 'prewar'
    if yr_start < 1990: return 'classic'
    if yr_start < 2005: return 'youngtimer'
    return 'modern'

# ── MODEL FAMILY : extrait le modele parent du mo ───────────────────────────
def derive_family(mk, mo):
    if not mo: return None
    m = mo.strip()
    # Porsche : 911 (992), 911 GT3 -> 911 ; 718 Cayman -> 718
    if mk == 'Porsche':
        mm = re.match(r'^(911|718|356|928|924|944|968|914|959|912|930|964|993|996|997|991|992|cayenne|panamera|macan|taycan|boxster|cayman)', m, re.I)
        if mm: return mm.group(1).upper() if mm.group(1).lower() in ('911','718','356','928','924','944','968','914','959','912') else mm.group(1).capitalize()
    # Ferrari : garder le numero/nom de base (812 Superfast -> 812)
    if mk == 'Ferrari':
        mm = re.match(r'^(\d{3}|f\d+|testarossa|daytona|enzo|laferrari|roma|portofino|california|mondial|ff|gtc4|monza|sf90|296|12\s*cilindri)', m, re.I)
        if mm: return mm.group(1).upper()
    # Lamborghini : premier mot
    if mk == 'Lamborghini':
        mm = re.match(r'^(countach|diablo|murcielago|aventador|gallardo|huracan|huracán|miura|espada|jarama|urus|urraco|jalpa|reventon|veneno|centenario|sian|revuelto)', m, re.I)
        if mm: return mm.group(1).capitalize()
    # BMW M : M3, M5...
    if mk == 'BMW':
        mm = re.match(r'^(m[1-8]\b|[1-8]\s*series|[1-8]er|x[1-7]|z[1-8]|i[3-8])', m, re.I)
        if mm: return mm.group(1).upper().replace(' ','')
    # Mercedes : C-Class, SL... garder la classe
    if mk == 'Mercedes-Benz':
        mm = re.match(r'^([a-z]+)[\s-]?(class|klasse)', m, re.I)
        if mm: return mm.group(1).upper()+'-Class'
        mm2 = re.match(r'^(sls|amg\s*gt|sl|slk|slc|clk|cls|cla|gla|glc|gle|gls|glk)', m, re.I)
        if mm2: return mm2.group(1).upper()
    # Defaut : premier token alphanum significatif
    mm = re.match(r'^([a-z0-9]+([\s-][a-z0-9]+)?)', m, re.I)
    return mm.group(1) if mm else None

# ── GENERATION CODE : (992), E46, W204 entre parentheses ou connus ──────────
def derive_generation(mo):
    if not mo: return None
    mm = re.search(r'\((\d{3}|[ewfg]\d{2,3}|[a-z]\d{2,3})\)', mo, re.I)
    if mm: return mm.group(1).upper()
    mm2 = re.search(r'\b(e\d{2}|f\d{2}|g\d{2}|w\d{3}|r\d{3})\b', mo, re.I)
    if mm2: return mm2.group(1).upper()
    return None

# Normalisation casse marque pour matching regles (NHTSA met en CAPS)
_MK_CANON = {'AUDI':'Audi','FERRARI':'Ferrari','PORSCHE':'Porsche','BMW':'BMW','MERCEDES-BENZ':'Mercedes-Benz','LAMBORGHINI':'Lamborghini','MASERATI':'Maserati','ASTON MARTIN':'Aston Martin','ALFA ROMEO':'Alfa Romeo','MCLAREN':'McLaren','NISSAN':'Nissan','TOYOTA':'Toyota','HONDA':'Honda','ACURA':'Acura','MAZDA':'Mazda','MITSUBISHI':'Mitsubishi','SUBARU':'Subaru','LOTUS':'Lotus','VOLKSWAGEN':'Volkswagen'}
def _canon_mk(mk):
    if not mk: return mk
    up = mk.strip().upper()
    return _MK_CANON.get(up, mk.strip())

def classify(row):
    """Retourne dict des colonnes regles pour une ligne models_canonical."""
    mk = _canon_mk(row.get('mk') or '')
    mo = (row.get('mo') or '').strip()
    mo_l = mo.lower()
    out = {}

    # engine_layout / engine_cyl
    for rule_mk, pat, layout, cyl in ENGINE_RULES:
        if mk == rule_mk and re.search(pat, mo_l):
            out['engine_layout'] = layout
            out['engine_cyl'] = cyl
            break

    # is_performance
    perf = mk in ALL_PERFORMANCE_MK
    if not perf and (out.get('engine_cyl',0) or 0) >= 8: perf = True
    if not perf and PERF_PAT.search(mo): perf = True
    # AMG lettre+nombre (C43, E53, A45...) chez Mercedes
    if not perf and mk=='Mercedes-Benz' and AMG_NUM_PAT.search(mo): perf = True
    # Familles sportives a 6/4 cyl sans mot-cle (911, M*, JDM icons, roadsters)
    fam_now = derive_family(mk, mo)
    SPORT_FAMILIES = {
        ('Porsche','911'),('Porsche','718'),('Porsche','Cayman'),('Porsche','Boxster'),('Porsche','959'),('Porsche','914'),('Porsche','944'),('Porsche','968'),('Porsche','Carrera GT'),
        ('Nissan','Skyline GT-R'),('Nissan','Skyline'),('Toyota','Supra'),('Toyota','GT86'),('Toyota','86'),('Toyota','MR2'),('Toyota','2000GT'),('Honda','NSX'),('Acura','NSX'),('Honda','S2000'),('Honda','Integra'),
        ('Mazda','RX-7'),('Mazda','RX-8'),('Mazda','MX-5'),('Mitsubishi','3000GT'),('Mitsubishi','GTO'),
        ('Alfa Romeo','4C'),('Alfa Romeo','8C'),('Alfa Romeo','Montreal'),('Lotus','Elise'),('Lotus','Exige'),('Lotus','Evora'),
    }
    if not perf and fam_now and (mk, fam_now) in SPORT_FAMILIES: perf = True
    # BMW M tout court (M1-M8) = performance
    if not perf and mk=='BMW' and re.match(r'^M[1-8]\b', mo, re.I): perf = True
    # BMW M Performance (M340i, M240i, M550i, X3 M40i...) = performance
    if not perf and mk=='BMW' and re.search(r'\bM\d{2,3}[a-z]|\bM\d{2,3}\b|\d{2}\s*M\b', mo, re.I): perf = True
    out['is_performance'] = perf

    # is_special_edition
    out['is_special_edition'] = bool(SPECIAL_PAT.search(mo))

    # is_competition
    out['is_competition'] = bool(COMPETITION_PAT.search(mo))

    # is_limited
    out['is_limited'] = bool(LIMITED_PAT.search(mo))

    # model_family
    fam = derive_family(mk, mo)
    if fam: out['model_family'] = fam

    # generation_code
    gen = derive_generation(mo)
    if gen: out['generation_code'] = gen

    # is_icon
    if fam and (mk, fam) in ICON_MODELS: out['is_icon'] = True

    # era
    era = derive_era(row.get('yr_start'))
    if era: out['era'] = era

    out['enrich_source'] = 'rules'
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mk', help='Limiter a une marque')
    ap.add_argument('--dry', action='store_true', help='Simulation sans ecriture')
    ap.add_argument('--resume', action='store_true', help='Ne traiter que les lignes pas encore enrichies (enrich_source NULL)')
    args = ap.parse_args()

    db = get_db()
    # Pagination cap 999 — query RECONSTRUITE a chaque page (sinon params empiles)
    rows = []
    offset = 0
    PAGE = 999
    while True:
        q = db.table('models_canonical').select('id,mk,mo,yr_start')
        if args.mk: q = q.eq('mk', args.mk)
        if args.resume: q = q.is_('enrich_source', 'null')
        q = q.order('id').range(offset, offset+PAGE-1)
        res = q.execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < PAGE: break
        offset += PAGE
    print(f"Lignes a traiter : {len(rows)}")

    updated = 0
    stats = {'engine_layout':0,'is_performance':0,'is_special_edition':0,'is_competition':0,'is_limited':0,'is_icon':0,'model_family':0,'generation_code':0,'era':0}
    for i, row in enumerate(rows):
        patch = classify(row)
        for k in stats:
            if patch.get(k): stats[k]+=1
        if args.dry:
            if i < 30:
                print(f"  {row['mk']:14s} | {str(row['mo'])[:28]:28s} -> layout={patch.get('engine_layout','-')} fam={patch.get('model_family','-')} perf={patch.get('is_performance')} spec={patch.get('is_special_edition')} comp={patch.get('is_competition')}")
            continue
        try:
            db.table('models_canonical').update(patch).eq('id', row['id']).execute()
        except Exception as e:
            # Reconnexion sur coupure HTTP/2 puis retry une fois
            print(f"  reconnexion (erreur: {str(e)[:60]})")
            time.sleep(1.0)
            db = get_db()
            db.table('models_canonical').update(patch).eq('id', row['id']).execute()
        updated += 1
        if updated % 200 == 0:
            print(f"  ...{updated} mis a jour")
            time.sleep(0.1)
        # Recreer le client tous les 500 updates (evite epuisement streams HTTP/2)
        if updated % 500 == 0:
            db = get_db()

    print(f"\n{'[DRY] ' if args.dry else ''}Termine. {updated} lignes mises a jour.")
    print("Stats (lignes avec flag/valeur) :")
    for k,v in sorted(stats.items(), key=lambda x:-x[1]):
        print(f"  {k:22s} {v}")

if __name__ == '__main__':
    main()
