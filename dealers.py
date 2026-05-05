"""
AutoRadar — Configuration des concessions luxe (v2)
═══════════════════════════════════════════════════════════════
Fichier : ~/Desktop/autoradar-scraper/dealers.py (REMPLACE l'ancien)

Liste curatée des concessions premium France / Belgique / Suisse / Luxembourg.
Version 2 : ajoute le champ optionnel 'selectors' pour parser CSS spécifique.

Format complet :
{
    'name':        'NomConcession',           # Identifiant unique (snake_case OK)
    'display':     'Nom Affichable',          # Nom dans la DB (champ src)
    'country':     'France|Belgique|Suisse|Luxembourg',
    'city':        'Genève',                  # Optionnel
    'base_url':    'https://www.exemple.com',
    'listing_url': 'https://www.exemple.com/stock',
    'pagination':  '?page={page}',            # Optionnel, None si pas de pagination
    'max_pages':   3,
    'use_stealth': False,                     # True si Cloudflare/anti-bot
    'tags':        ['Premium', 'Concession'], # Tags ajoutés aux annonces (DB.opts)
    'spec':        'Note interne',
    'inactive':    False,                     # True = skipped par le scraper
    'selectors':   {                          # Optionnel - parser dédié
        'card':    'a[href*="/car/"]',        # Sélecteur des cards (obligatoire si selectors présent)
        'title':   'h3, h4',                  # Sélecteur titre (relatif à la card)
        'price':   ':contains("CHF"), :contains("€")',  # Sélecteur prix
        'km':      None,                      # Souvent absent en listing, OK
        'year':    None,                      # Souvent absent en listing, OK
        'link':    'self',                    # 'self' = la card EST le lien (sinon sélecteur)
    },
}

Stratégie business : commission apporteur d'affaires 1-3% sur les ventes facilitées.
"""

DEALERS = [
    # ════════════════════════════════════════════════════════════
    # 🇫🇷 FRANCE
    # ════════════════════════════════════════════════════════════
    {
        'name': 'moteuretsens',
        'display': 'Moteur & Sens',
        'country': 'France',
        'city': 'Lyon',
        'base_url': 'https://moteuretsens.com',
        'listing_url': 'https://moteuretsens.com/voitures-disponibles/',
        'pagination': '?page={page}',
        'max_pages': 3,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Sport'],
        'spec': 'Leader FR voitures sport occasion',
        # parser générique fonctionne (3 voitures extraites)
    },
    {
        'name': 'excelcar',
        'display': 'Excel Car',
        'country': 'France',
        'city': 'Rivesaltes',
        'base_url': 'https://www.excelcar66.com',
        'listing_url': 'https://www.excelcar66.com/voitures/',
        'pagination': '/page/{page}/',
        'max_pages': 3,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Supercar'],
        'spec': 'Ferrari, Lamborghini, Aston Martin — 250 ventes/an',
        # parser générique fonctionne mais bug _extract_price → fixé en v2
    },
    {
        'name': 'db7autos',
        'display': 'DB7 Autos',
        'country': 'France',
        'city': 'Guérande',
        'base_url': 'https://www.db7autos.fr',
        'listing_url': 'https://www.db7autos.fr/voiture-luxe-occasion-paris/23-18.htm',
        'pagination': None,
        'max_pages': 1,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Aston Martin'],
        'spec': 'Aston Martin, Ferrari, Maserati, Bentley',
        # 6 cards trouvées mais parser ne sort rien — DB7 utilise probablement
        # un framework propriétaire avec des classes non-standard.
        # À inspecter dans une 2e vague.
    },
    {
        'name': 'eliandre',
        'display': 'Eliandre Automobile',
        'country': 'France',
        'city': 'Paris',
        'base_url': 'https://www.eliandre-auto.com',
        'listing_url': 'https://www.eliandre-auto.com/vehicules-occasion-paris/',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Collection'],
        'spec': 'Porsche, Jaguar, classiques',
        # 0 cards trouvées — sélecteurs CSS personnalisés à investiguer
    },
    {
        'name': 'evocars',
        'display': 'EvoCars',
        'country': 'France',
        'city': 'Villefranche-sur-Saône',
        'base_url': 'https://www.evocars.fr',
        'listing_url': 'https://www.evocars.fr/vehicules/',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Sport'],
        'spec': 'Porsche, sport — dépôt-vente',
        # parser générique fonctionne (1 voiture extraite)
    },
    {
        'name': 'bstore',
        'display': 'BStore Auto Prestige',
        'country': 'France',
        'city': 'Aix-en-Provence',
        'base_url': 'https://www.bstore-voituredeluxe.fr',
        'listing_url': 'https://www.bstore-voituredeluxe.fr/voiture-de-luxe.php',
        'pagination': None,
        'max_pages': 1,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Morgan'],
        'spec': 'Multi-luxe + concessionnaire Morgan',
        # ERR_NAME_NOT_RESOLVED pendant les tests — possiblement DNS local cassé,
        # le site est officiellement live (vérifié via web search).
        # À retester. Pas de inactive=True pour l'instant.
    },
    {
        'name': 'econcession',
        'display': 'e-Concession Bordeaux',
        'country': 'France',
        'city': 'Bordeaux',
        'base_url': 'https://www.drivinbordeaux.fr',
        'listing_url': 'https://www.drivinbordeaux.fr/e-concession-automobile',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession'],
        'spec': 'Premium/sport Bordeaux',
        # 1 card trouvée mais parser ne sort rien
    },

    # ════════════════════════════════════════════════════════════
    # 🇧🇪 BELGIQUE
    # ════════════════════════════════════════════════════════════
    {
        'name': 'bavariamotors',
        'display': 'Bavaria Motors',
        'country': 'Belgique',
        'city': 'Harelbeke',
        'base_url': 'https://www.bavariamotors.be',
        # CORRIGÉ : nouvelle URL listing identifiée par inspection
        'listing_url': 'https://www.bavariamotors.be/fr/aanbod-te-koop',
        'pagination': '?page={page}',
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Sport', 'Porsche'],
        'spec': 'Porsche spécialiste, classiques — Harelbeke',
        # Sélecteur dédié : les cards sont dans /wagens/{id}-{slug}
        'selectors': {
            'card': 'a[href*="/wagens/"]',
            'title': 'h2, h3, h4, .title, [class*="title"]',
            'price': '[class*="price"], [class*="prijs"]',  # prijs = prix en flamand
        },
    },
    {
        'name': 'kuurnemotors',
        'display': 'Kuurne Motors',
        'country': 'Belgique',
        'city': 'Kuurne',
        'base_url': 'https://www.kuurnemotors.fr',
        'listing_url': 'https://www.kuurnemotors.fr/voiture-occasion-belgique-fr-fr.htm',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession'],
        'spec': 'Premium 30 ans expérience',
        # 0 cards — site probablement listing dynamique JS
    },

    # ════════════════════════════════════════════════════════════
    # 🇨🇭 SUISSE — marché le plus dense d'Europe
    # ════════════════════════════════════════════════════════════
    {
        'name': 'carugati',
        'display': 'Carugati Automobiles',
        'country': 'Suisse',
        'city': 'Plan-les-Ouates (Genève)',
        'base_url': 'https://www.carugati.ch',
        'listing_url': 'https://www.carugati.ch/inventory/',
        'pagination': '?page={page}',
        'max_pages': 3,
        'use_stealth': True,  # site corporate, anti-bot probable
        'tags': ['Premium', 'Concession', 'Ferrari', 'Pagani'],
        'spec': '40 ans Ferrari, ex-importateur Pagani Suisse 16 ans ⭐⭐',
    },
    {
        'name': 'pereggocars',
        'display': 'Perego Cars',
        'country': 'Suisse',
        'city': 'Etoy',
        'base_url': 'https://www.peregocars.com',
        # CORRIGÉ : la vraie URL listing
        'listing_url': 'https://www.peregocars.com/cars-for-sale',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Supercar'],
        'spec': 'Porsche, Ferrari, McLaren, Lamborghini, Mercedes-AMG',
        # Site charge listing en JavaScript (HighLevel/GoHighLevel framework).
        # Notre Playwright "networkidle" devrait capturer après JS render.
    },
    {
        'name': 'lambogeneve',
        'display': 'Lamborghini Genève',
        'country': 'Suisse',
        'city': 'Plan-les-Ouates (Genève)',
        'base_url': 'https://new.lamborghinigeneve.ch',
        'listing_url': 'https://new.lamborghinigeneve.ch/nos-vehicules-en-stock/lamborghini-en-stock/',
        'pagination': '?page={page}',
        'max_pages': 2,
        'use_stealth': True,
        'tags': ['Premium', 'Concession', 'Lamborghini', 'Officiel'],
        'spec': 'Concession officielle Lamborghini',
    },
    {
        'name': 'lamboporrentruy',
        'display': 'Garage R. Affolter',
        'country': 'Suisse',
        'city': 'Porrentruy',
        'base_url': 'https://lamborghiniporrentruy.com',
        # CORRIGÉ : la vraie URL listing (vue de leur site)
        'listing_url': 'https://lamborghiniporrentruy.com/en-stock/',
        'pagination': '/page/{page}/',
        'max_pages': 5,  # 16 pages au total, on prend les 5 premières
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Lamborghini', 'Officiel'],
        'spec': 'Lamborghini Suisse, multimarques (Porsche, Ferrari, McLaren, Bugatti) — 200-250 véhicules/an',
        # Sélecteur dédié : structure `a[href*="/car/"]` avec h3 (marque) + h4 (modèle) + texte CHF
        'selectors': {
            'card': 'a[href*="/car/"], a[href*="/en-stock/"]',
            'title': 'h3, h4',
            'price': None,  # Le prix est dans le texte brut, on le détecte par regex CHF
        },
    },
    {
        'name': 'modenacars',
        'display': 'Modena Cars',
        'country': 'Suisse',
        'city': 'Plan-les-Ouates (Genève)',
        'base_url': 'https://www.modena-cars.ch',
        'listing_url': 'https://www.modena-cars.ch/fr/voitures-occasion',
        'pagination': '?page={page}',
        'max_pages': 2,
        'use_stealth': True,
        'tags': ['Premium', 'Concession', 'Ferrari', 'Maserati', 'Officiel'],
        'spec': 'Ferrari et Maserati Suisse romande',
    },
    {
        'name': 'rrgeneva',
        'display': 'Rolls-Royce Motor Cars Geneva',
        'country': 'Suisse',
        'city': 'Nyon',
        'base_url': 'https://www.rolls-roycemotorcars-geneva.ch',
        'listing_url': 'https://www.rolls-roycemotorcars-geneva.ch/preowned/',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': True,
        'tags': ['Premium', 'Concession', 'Rolls-Royce', 'Officiel'],
        'spec': 'Concession officielle Rolls-Royce + Aston Martin',
    },

    # ════════════════════════════════════════════════════════════
    # 🇱🇺 LUXEMBOURG
    # ════════════════════════════════════════════════════════════
    {
        'name': 'schumachermotors',
        'display': 'Schumacher Motors',
        'country': 'Luxembourg',
        'city': 'Luxembourg',
        'base_url': 'https://www.schumacher-motors.com',
        'listing_url': 'https://www.schumacher-motors.com/galerie',
        'pagination': '?page={page}',
        'max_pages': 3,
        'use_stealth': True,
        'tags': ['Premium', 'Concession', 'Bugatti', 'Pagani', 'Koenigsegg'],
        'spec': 'Bugatti, Pagani, Koenigsegg, McLaren ⭐⭐⭐ La pépite',
    },
    {
        'name': 'prestigegt',
        'display': 'Prestige GT Luxembourg',
        'country': 'Luxembourg',
        'city': 'Luxembourg',
        'base_url': 'https://www.prestigegt.com',
        'listing_url': 'https://www.prestigegt.com/voitures-occasion',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession'],
        'spec': 'Multi-luxe LU+FR+BE+DE, courtage spécialisé',
        # ERR_TOO_MANY_REDIRECTS pendant les tests — boucle de redirection
        # Marqué inactif tant qu'on ne trouve pas la bonne URL
        'inactive': True,
        'inactive_reason': 'redirect_loop — URL listing à corriger',
    },
    {
        'name': 'luxsellect',
        'display': 'LuxSELLect',
        'country': 'Luxembourg',
        'city': 'Fentange',
        'base_url': 'https://luxsellect.lu',
        'listing_url': 'https://luxsellect.lu/inventory',
        'pagination': None,
        'max_pages': 2,
        'use_stealth': False,
        'tags': ['Premium', 'Concession', 'Collection'],
        'spec': 'Luxe + collection depuis 2010',
    },
    {
        'name': 'dealndrive',
        'display': 'Deal & Drive',
        'country': 'Luxembourg',
        'city': 'Luxembourg',
        'base_url': 'https://www.dealndrive.com',
        'listing_url': 'https://www.dealndrive.com/inventory',
        'pagination': '?page={page}',
        'max_pages': 3,
        'use_stealth': False,
        'tags': ['Premium', 'Concession'],
        'spec': '50+ marques, contrôle 100 points',
    },
]


# ─── Helpers ───
def get_dealer_by_name(name: str) -> dict:
    """Retourne la config d'une concession par son nom (case-insensitive)."""
    name_lower = name.lower().strip()
    for d in DEALERS:
        if d['name'].lower() == name_lower:
            return d
    raise ValueError(f"Concession '{name}' inconnue. Concessions disponibles : "
                     f"{', '.join(d['name'] for d in DEALERS)}")


def get_dealer_names() -> list:
    """Liste des noms de concessions (pour CLI choices)."""
    return [d['name'] for d in DEALERS]


def get_dealers_by_country(country: str) -> list:
    """Filtre les concessions par pays."""
    return [d for d in DEALERS if d['country'].lower() == country.lower()]


def get_active_dealers() -> list:
    """Retourne uniquement les concessions actives (non marquées inactive)."""
    return [d for d in DEALERS if not d.get('inactive', False)]


# ─── Test rapide ───
if __name__ == "__main__":
    print("═" * 65)
    print("AutoRadar — Concessions partenaires (v2)")
    print("═" * 65)

    by_country = {}
    for d in DEALERS:
        by_country.setdefault(d['country'], []).append(d)

    flag = {'France': '🇫🇷', 'Belgique': '🇧🇪', 'Suisse': '🇨🇭', 'Luxembourg': '🇱🇺'}
    for country in ['France', 'Belgique', 'Suisse', 'Luxembourg']:
        dealers = by_country.get(country, [])
        active = [d for d in dealers if not d.get('inactive')]
        print(f"\n{flag.get(country, '🌍')} {country.upper()} ({len(active)}/{len(dealers)} actives) :")
        for d in dealers:
            inactive_tag = ' ⏸️  INACTIF' if d.get('inactive') else ''
            stealth = ' 🥷' if d.get('use_stealth') else ''
            custom_sel = ' 🎯' if d.get('selectors') else ''
            print(f"    • {d['display']:<35} ({d['city']}){stealth}{custom_sel}{inactive_tag}")

    total_active = len(get_active_dealers())
    total_pages = sum(d['max_pages'] for d in get_active_dealers())
    stealth_count = sum(1 for d in get_active_dealers() if d.get('use_stealth'))
    custom_count = sum(1 for d in get_active_dealers() if d.get('selectors'))
    print()
    print(f"📊 Total : {total_active}/{len(DEALERS)} concessions actives, "
          f"~{total_pages} pages/run, {stealth_count} stealth, {custom_count} avec parser dédié")
    print()
    print("Légende : 🥷 = stealth Cloudflare · 🎯 = parser CSS dédié · ⏸️  = désactivé")
