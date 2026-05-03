"""
AutoRadar — Système de batches scraping
═══════════════════════════════════════════════════════════════
À placer dans : ~/Desktop/autoradar-scraper/batches.py

Définit 3 groupes de sources selon le risque juridique :
- GREEN : sites de niche/collection, CGU permissives → exploit max, 2x/jour
- YELLOW : sites grands publics avec CGU regardantes → exploit modéré, 1x/jour
- RED : sites avec historique de poursuites → AUCUN scraping auto

Usage :
    python3 scraper.py --batch green    # toutes les sources vertes
    python3 scraper.py --batch yellow   # toutes les sources jaunes
    python3 scraper.py --source <name>  # une source spécifique (manuel)

Les sources RED ne sont PAS automatiquement lancées avec --batch.
Pour les lancer (à tes risques), il faut explicitement :
    python3 scraper.py --source leboncoin --pages N
"""

# ─── BATCH GREEN — Sites de collection/niche, exploit max ───
# Ces sources ont des CGU permissives ou ne se sont jamais opposées
# au scraping de leurs annonces. Ce sont aussi les plus pertinentes
# pour le marché passionnés/bolides (Bugatti, Pagani, Ferrari).
GREEN_SOURCES = [
    'lesanciennes',     # Collection FR, ✅ marche actuellement
    'oldtimerfarm',     # Spécialiste belge collection
    'classictrader',    # International collection
    'goodtimers',       # Magazine + annonces
    'dyler',            # International luxe/sport
    'classicnumber',    # n°1 FR collection (à débloquer Cloudflare)
    'gotothegrid',      # Sport/compétition (à débloquer)
    'racemarket',       # Rally/circuit (à débloquer)
    'classicdriver',    # Luxe européen (à débloquer)
    'plethore',         # Premium FR (à débloquer)
    'carjager',         # Réseau privé expertisé (à débloquer)
    'collectingcars',   # UK enchères premium
    'superclassics',    # Européen prestige
    'jenden',           # Enchères collection
    'carandclassic',    # UK classic
    'pistonheads',      # UK sport/classic
    'kleinanzeigen',    # DE oldtimer
]

# Cadence batch GREEN : 2 fois par jour
GREEN_PAGES = 5  # max pages par run, par source

# ─── BATCH YELLOW — Grands publics, CGU regardantes mais OK ───
# Ces sources ont des CGU explicitement anti-scraping mais pas
# d'historique d'attaques contre petits agrégateurs. À traiter
# avec respect : faible cadence, espacement des requêtes.
YELLOW_SOURCES = [
    'autoscout24',      # Plus grosse source actuelle (445 cars)
    '2ememain',         # Marché belge généraliste
    'gocar',            # Belgique
    'autolive',         # Belgique
    'tutti',            # Suisse
    'anibis',           # Suisse
    'car4you',          # Suisse spécialiste
    'luxauto',          # Luxembourg référence
    'automarket',       # Luxembourg
    'autolu',           # Luxembourg particuliers
    'mobile',           # Allemagne (à débloquer)
    'vroom',            # Belgique (à débloquer)
    'ofa',              # OuestFrance auto
    'marktplaats',      # Pays-Bas
    'subito',           # Italie
    'wallapop',         # Espagne
    'willhaben',        # Autriche
    'otomoto',          # Pologne
    'blocket',          # Suède
]

# Cadence batch YELLOW : 1 fois par jour
YELLOW_PAGES = 3  # max pages par run, plus prudent

# ─── BATCH RED — INTERDIT EN AUTO ───
# Ces sources ont attaqué juridiquement des scrapers similaires.
# JAMAIS dans le batch automatique. Lancement manuel uniquement
# avec --source <name> --pages N à tes risques et périls.
RED_SOURCES = [
    'leboncoin',        # ⚠️ A poursuivi Jinka, Bien'ici, etc.
    'lacentrale',       # ⚠️ DataDome anti-bot, gros groupe média
    'fb-fr',            # ⚠️ Meta interdit explicitement
    'fb-be',            # ⚠️ Idem
    'fb-ch',            # ⚠️ Idem
    'ebay-fr',          # ⚠️ Pollution actuelle non résolue
    'ebay-be',
    'ebay-ch',
]


def get_sources_for_batch(batch_name: str) -> list:
    """Retourne la liste de sources pour un batch donné."""
    batch_name = batch_name.lower().strip()
    if batch_name == 'green':
        return GREEN_SOURCES
    if batch_name == 'yellow':
        return YELLOW_SOURCES
    if batch_name == 'red':
        # On retourne RED mais avec un warning clair côté caller
        return RED_SOURCES
    if batch_name == 'all-safe':
        # Combine green + yellow, exclut red
        return GREEN_SOURCES + YELLOW_SOURCES
    raise ValueError(f"Batch inconnu : '{batch_name}'. Utilise green, yellow, red, ou all-safe.")


def get_pages_for_batch(batch_name: str) -> int:
    """Retourne le nombre de pages recommandé par source pour un batch."""
    batch_name = batch_name.lower().strip()
    if batch_name == 'green':
        return GREEN_PAGES
    if batch_name == 'yellow':
        return YELLOW_PAGES
    if batch_name == 'red':
        return 1  # Si jamais lancé manuellement, profondeur minimale
    if batch_name == 'all-safe':
        return GREEN_PAGES  # On utilise green par défaut
    return 1


def is_red_source(source_name: str) -> bool:
    """Vrai si la source nécessite un consentement explicite manuel."""
    return source_name.lower().strip() in [s.lower() for s in RED_SOURCES]


# ─── Test rapide ───
if __name__ == "__main__":
    print("═" * 60)
    print("AutoRadar — Configuration des batches")
    print("═" * 60)
    print(f"\n🟢 GREEN ({len(GREEN_SOURCES)} sources, {GREEN_PAGES} pages, 2x/jour) :")
    for s in GREEN_SOURCES:
        print(f"    • {s}")
    print(f"\n🟡 YELLOW ({len(YELLOW_SOURCES)} sources, {YELLOW_PAGES} pages, 1x/jour) :")
    for s in YELLOW_SOURCES:
        print(f"    • {s}")
    print(f"\n🔴 RED ({len(RED_SOURCES)} sources — JAMAIS en auto) :")
    for s in RED_SOURCES:
        print(f"    • {s}  ⚠️")
    print(f"\nTotal scrapable en auto : {len(GREEN_SOURCES) + len(YELLOW_SOURCES)} sources")
