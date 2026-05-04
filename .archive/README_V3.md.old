# AutoRadar — Refonte v3 Concessions

Pack de fichiers pour passer le système de concessions de "fonctionne sur 3" à "fonctionne sur 12-15".

## Ce que ce pack apporte

🎯 **Parser CSS dédié par concession** — chaque site peut spécifier ses propres sélecteurs
🥷 **Stealth browser corrigé** — fix du bug asyncio loop qui bloquait 5 sites Cloudflare
💰 **Extraction prix robuste** — multi-devises (€/CHF/$/£), anti-concat, plage 500€-5M€
📁 **HTML dump automatique** — sauvegarde debug/{name}.html pour les concessions à analyser
📊 **Test runner avec rapport markdown** — `python3 test_dealers.py` → rapport complet

## Installation (4 étapes)

### 1. Sauvegarde de sécurité

```
cd ~/Desktop/autoradar-scraper
cp scraper.py scraper.py.before_v3_manual
cp dealers.py dealers.py.before_v3_manual
cp stealth_browser.py stealth_browser.py.before_v3_manual
```

### 2. Remplace les fichiers

Télécharge depuis le chat les 4 fichiers du pack v3 et place-les dans `~/Desktop/autoradar-scraper/` :

- `dealers.py` (REMPLACE l'ancien)
- `stealth_browser.py` (REMPLACE l'ancien)
- `apply_v3_patch.py` (NOUVEAU)
- `test_dealers.py` (NOUVEAU)

```
cp ~/Downloads/dealers.py .
cp ~/Downloads/stealth_browser.py .
cp ~/Downloads/apply_v3_patch.py .
cp ~/Downloads/test_dealers.py .
```

### 3. Vérification config dealers v2

```
python3 dealers.py
```

Tu dois voir le récap des 19 concessions avec :
- Total : 18/19 actives (Prestige GT marqué inactif)
- 5 stealth (🥷)
- 2 avec parser dédié (🎯) : Bavaria Motors, Affolter

### 4. Application du patch sur scraper.py

```
python3 apply_v3_patch.py
```

Tu dois voir 4 patches OK + syntaxe valide. Le scraper.py est sauvegardé en `scraper.py.before_v3`.

### 5. Vérification import

```
python3 -c "import scraper; print('OK')"
```

## Tests

### Test rapide (1 concession)

```
# Test fix _extract_price (Excel Car)
python3 scraper.py --dealer excelcar --pages 1

# Test selectors dédiés + correctif URL (Affolter — gros stock Lambo)
python3 scraper.py --dealer lamboporrentruy --pages 1

# Test selectors dédiés + correctif URL (Bavaria Motors)
python3 scraper.py --dealer bavariamotors --pages 1

# Test stealth fix (Schumacher Motors — la pépite Bugatti/Pagani)
python3 scraper.py --dealer schumachermotors --pages 1
```

### Test complet automatisé

```
python3 test_dealers.py
```

Lance les 18 concessions actives en série (~10-15 minutes) et génère un rapport markdown détaillé `test_report_YYYYMMDD_HHMMSS.md` avec :
- Statistiques globales (cards/extraits/new/rejets)
- Tableau récapitulatif coloré
- Sections par status (🟢🟡🟠🔴)
- Recommandations d'actions par concession

```
# Variantes
python3 test_dealers.py --country France      # Que la France
python3 test_dealers.py --country Suisse      # Que la Suisse
python3 test_dealers.py --only excelcar       # Une seule
python3 test_dealers.py --pages 2             # Plus de pages par concession
```

### Inspection des HTML dumps

Pour les concessions qui sortent 0 listings, le scraper sauvegarde automatiquement le HTML rendu dans `debug/`. Très utile pour identifier les bons sélecteurs CSS sans avoir à inspecter manuellement chaque site.

```
ls debug/
# pereggocars_p1.html
# kuurnemotors_p1.html
# eliandre_p1.html
# ...

# Inspection rapide d'un dump
grep -o 'class="[^"]*car[^"]*"' debug/pereggocars_p1.html | sort -u
```

## Ce qui change vs v2

| | v2 | v3 |
|---|---|---|
| Stealth browser | ❌ Bug asyncio loop systématique | ✅ Fonctionne (init script JS pur) |
| Parser dealers | Générique uniquement | Générique + dédié par CSS |
| Extract price | `r'(\d[\d\s]*)\s*€'` (concat tous prix) | Multi-devises strict, cap 5M€ |
| Bavaria Motors | URL fausse | URL `/fr/wagens` corrigée |
| Affolter Lambo | URL fausse | URL `/en-stock/` corrigée |
| Prestige GT | redirect loop | marqué inactif |
| Debug | Manuel | HTML dumps auto vers debug/ |
| Test | Manuel `--dealer` un par un | Runner + rapport markdown |

## Concessions avec parser dédié (déjà configuré)

🎯 **Bavaria Motors** (Belgique) — sélecteur `a[href*="/wagens/"]`
🎯 **Garage R. Affolter** (Suisse, Lambo Porrentruy) — sélecteur `a[href*="/car/"]`

Pour ajouter un parser dédié à une autre concession, édite `dealers.py` et ajoute le champ `selectors` :

```python
{
    'name': 'monouvelle',
    # ... config existante ...
    'selectors': {
        'card': 'a.vehicle-card',           # Sélecteur des cards
        'title': 'h3, h4, .title',          # Sélecteur titre (relatif card)
        'price': '.price, [class*="prix"]', # Sélecteur prix
    },
},
```

Le parser dédié extrait automatiquement année et km depuis le texte de la card via regex robuste.

## Concessions encore à configurer (faciles)

Après application du patch, ces concessions auront probablement encore besoin de selectors spécifiques. Inspecte leurs HTML dumps et ajoute le champ `selectors` :

- **Eliandre Automobile** (0 cards trouvées)
- **Kuurne Motors** (0 cards)
- **Deal & Drive** (0 cards)
- **DB7 Autos** (6 cards mais parser muet)
- **Perego Cars** (43 cards mais parser muet — listing JS à fort potentiel)
- **e-Concession Bordeaux** (1 card mais parser muet)
- **LuxSELLect** (1 card mais parser muet)

Ouvre `debug/{name}_p1.html` dans ton navigateur, inspecte la structure (Cmd+Opt+I), trouve les classes CSS des cards et ajoute-les dans `dealers.py`.

## Annulation

Si quelque chose foire :

```
cp scraper.py.before_v3 scraper.py
cp scraper.py.before_v3_manual scraper.py    # safety backup
```

## État cible après application

| Concession | Avant | Après attendu |
|---|---|---|
| Moteur & Sens | 3 ✅ | 3-10 ✅ |
| Excel Car | 1 + 3 rejetés | 4-8 ✅ (fix prix) |
| EvoCars | 1 ✅ | 1-3 ✅ |
| **Affolter (Lamborghini)** | 0 | **15-25 ✅** (selectors + URL fix) |
| **Bavaria Motors** | 0 | **5-10 ✅** (selectors + URL fix) |
| **Schumacher** | erreur | **à voir** (stealth fix) |
| **Carugati / Lambo Genève / Modena / RR Geneva** | erreur | **à voir** (stealth fix) |
| Autres | 0 | encore 0 (à inspecter) |

Estimation après cette session : **passage de 3 → 8-12 concessions opérationnelles**, soit ~200-500 voitures luxe en DB.
