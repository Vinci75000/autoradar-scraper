# AutoRadar — Patch phase_a_scraper.py to use DedupCache

3 modifications chirurgicales à appliquer dans `phase_a_scraper.py`. Chaque bloc est petit, indépendant, testable.

---

## Patch 1 — Imports (en haut du fichier)

**Trouve** la ligne :
```python
from scraper_sources import SOURCES as _SOURCES_BASE
```

**Remplace par** :
```python
from scraper_sources import SOURCES as _SOURCES_BASE
from dedup import DedupCache
```

---

## Patch 2 — `SourceScraper.scrape_all()` avec dedup intégré

**Trouve** la méthode `scrape_all` actuelle :

```python
    def scrape_all(self, *, limit=None):
        urls = self.discover_urls()
        self.log.info(f"discovered {len(urls)} URLs for {self.slug}")
        for i, url in enumerate(urls):
            if limit and i >= limit: break
            car = self.scrape_listing(url)
            if car: yield car
            time.sleep(DELAY_BETWEEN_REQUESTS)
```

**Remplace par** :

```python
    def scrape_all(self, *, limit=None, db=None):
        """
        Discover URLs from sitemap/listings, scrape each, yield car dicts.
        
        If `db` is provided, uses DedupCache for 3-level early skip:
          L1: skip URL if already in DB                  (saves a GET)
          L3: skip if content_hash matches last fetch    (saves an insert)
        L2 (fingerprint cross-source) happens after parsing — it needs the car data.
        Caller is responsible for the L2 check after yield.
        
        If `db` is None, no dedup: scrapes everything (legacy behavior).
        """
        urls = self.discover_urls()
        self.log.info(f"discovered {len(urls)} URLs for {self.slug}")
        
        # Initialize dedup cache if DB available
        cache = None
        if db is not None:
            cache = DedupCache(db, self.cfg["display_name"], source_slug=self.slug)
            cache.load()
        
        # Track URLs we re-encountered (for last_seen_at lifecycle bump)
        rediscovered_urls = []
        
        for i, url in enumerate(urls):
            if limit and i >= limit:
                break
            
            if cache:
                cache.stats["urls_total"] += 1
                
                # L1 — URL already known: skip the GET entirely
                if cache.seen_url(url):
                    cache.stats["skipped_url"] += 1
                    rediscovered_urls.append(url)
                    continue
            
            # Fetch the page (raw HTML kept for content hashing)
            try:
                r = self.client.get(url)
            except Exception as e:
                self.log.warning(f"GET {url} failed: {e}")
                continue
            if r.status_code != 200:
                continue
            
            # L3 — content hash check
            content_hash = ""
            if cache:
                content_hash = cache.hash_content(r.text)
                if cache.seen_content_hash(url, content_hash):
                    cache.stats["skipped_content"] += 1
                    rediscovered_urls.append(url)
                    continue
                cache.stats["fetched"] += 1
            
            # Parse the response (reuses scrape_listing's logic)
            method = self.cfg.get("extraction", "selectors")
            if method == "jsonld":
                car = self._extract_jsonld(r.text)
            elif method == "selectors":
                car = self._extract_selectors(r.text)
            else:
                car = None
            
            if car:
                # Inject metadata
                car["src"] = self.cfg["display_name"]
                car["src_url"] = url
                car["_content_hash"] = content_hash  # caller can pass to insert_car if needed
                if not car.get("ci"): car["ci"] = self.cfg.get("city") or ""
                if not car.get("co"): car["co"] = self.cfg.get("country") or "France"
                if not car.get("lat"): car["lat"] = self.cfg.get("lat")
                if not car.get("lng"): car["lng"] = self.cfg.get("lng")
                
                # Attach cache reference for caller (so it can do L2 + mark_inserted)
                car["_dedup_cache"] = cache
                
                yield car
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Bump last_seen_at for URLs we re-encountered (lifecycle tracking)
        if cache and rediscovered_urls:
            updated = cache.bump_seen_urls(rediscovered_urls)
            self.log.info(f"bumped last_seen_at on {updated} re-encountered URLs")
        
        # Persist dedup stats to DB
        if cache:
            cache.flush_stats()
            self.log.info(cache.summary())
```

---

## Patch 3 — `_scrape_one_into_db()` avec L2 fingerprint check

**Trouve** la fonction `_scrape_one_into_db`, et **dans la boucle `for raw in scraper.scrape_all(limit=limit):`**, après `counters["yielded"] += 1` mais avant `try: car = dict_to_carlisting(raw)`:

**Trouve** ce bloc :

```python
def _scrape_one_into_db(slug, *, limit=None, insert_car=None, db=None, verbose=True):
    counters = {"yielded": 0, "valid": 0, "inserted": 0,
                "duplicate_or_invalid": 0, "convert_failed": 0, "error": 0}

    with SourceScraper(slug) as scraper:
        for raw in scraper.scrape_all(limit=limit):
            counters["yielded"] += 1
            try:
                car = dict_to_carlisting(raw)
```

**Remplace par** :

```python
def _scrape_one_into_db(slug, *, limit=None, insert_car=None, db=None, verbose=True):
    counters = {"yielded": 0, "valid": 0, "inserted": 0,
                "duplicate_or_invalid": 0, "convert_failed": 0,
                "skipped_cross_source": 0, "error": 0}

    with SourceScraper(slug) as scraper:
        # Pass db to enable L1/L3 dedup inside scrape_all
        for raw in scraper.scrape_all(limit=limit, db=db):
            counters["yielded"] += 1
            
            # L2 — fingerprint cross-source check (do BEFORE expensive insert)
            cache = raw.pop("_dedup_cache", None)
            content_hash = raw.pop("_content_hash", "")
            
            if cache and raw.get("mk") and raw.get("yr") and raw.get("km"):
                fp = cache.compute_fingerprint(
                    raw["mk"], raw.get("mo", ""), raw["yr"], raw["km"]
                )
                existing = cache.seen_fingerprint(fp)
                if existing and existing.get("src") != raw.get("src"):
                    # Same car listed at another dealer — record the cross-source link
                    cache.record_cross_source_match(
                        primary_car_id=existing["car_id"],
                        fp_hash=fp,
                        matched_url=raw["src_url"],
                        matched_src=raw["src"],
                    )
                    cache.stats["skipped_fp"] += 1
                    counters["skipped_cross_source"] += 1
                    if verbose:
                        print(f"  ⇄ cross-source match: {raw['mk']} {raw.get('mo','')} "
                              f"already at {existing.get('src')}")
                    continue
            
            # Standard pipeline: convert -> insert
            try:
                car = dict_to_carlisting(raw)
```

(Le reste de la fonction reste tel quel — convert_failed handling, insert_car call, etc.)

**Et juste après l'`insert_car()` qui réussit**, ajoute le `mark_inserted` :

**Trouve** :

```python
            try:
                result = insert_car(db, car)
                if result:
                    counters["inserted"] += 1
                    if verbose:
                        print(f"  ✓ {car.mk} {car.mo} {car.yr} — {car.km}km — {car.px}€")
```

**Remplace par** :

```python
            try:
                result = insert_car(db, car)
                if result and result != "rejected":
                    counters["inserted"] += 1
                    # Update dedup cache with the newly inserted car
                    if cache:
                        fp = cache.compute_fingerprint(car.mk, car.mo, car.yr, car.km)
                        cache.mark_inserted(car.src_url, fp, result, content_hash)
                    if verbose:
                        print(f"  ✓ {car.mk} {car.mo} {car.yr} — {car.km}km — {car.px}€")
```

---

## Patch 4 — Affichage des nouveaux compteurs

**Trouve** le bloc d'affichage final dans `_cli_scrape` :

```python
    print(f"\n{'='*60}")
    print(f"  yielded              = {c['yielded']}")
    print(f"  valid CarListing     = {c['valid']}")
    print(f"  inserted in Supabase = {c['inserted']}")
    print(f"  duplicate or invalid = {c['duplicate_or_invalid']}")
    print(f"  convert_failed       = {c['convert_failed']}")
    print(f"  errors               = {c['error']}")
```

**Remplace par** :

```python
    print(f"\n{'='*60}")
    print(f"  yielded                 = {c['yielded']}")
    print(f"  valid CarListing        = {c['valid']}")
    print(f"  inserted in Supabase    = {c['inserted']}")
    print(f"  duplicate or invalid    = {c['duplicate_or_invalid']}")
    print(f"  cross-source matched    = {c.get('skipped_cross_source', 0)}")
    print(f"  convert_failed          = {c['convert_failed']}")
    print(f"  errors                  = {c['error']}")
```

Idem dans `_cli_scrape_all_ready` (le bloc `GRAND TOTAL`).

---

## Test progressif après les 4 patches

### 1. Apply migration SQL
Lance `dedup_migration.sql` dans Supabase SQL editor. Vérifier :

```sql
select column_name from information_schema.columns
where table_schema = 'public' and table_name = 'cars'
  and column_name in ('first_seen_at', 'last_seen_at', 'times_seen', 'content_hash');
-- expected: 4 rows
```

### 2. Smoke test du module dedup tout seul

```bash
cd ~/Desktop/autoradar-scraper
python3 dedup.py inspect auto-selection
```

Sortie attendue (si auto-selection a déjà des cars en DB) :
```
[auto-selection] DedupCache loaded in 250ms — 2479 URLs, 4823 fingerprints
[auto-selection] total=0 skip_url=0 ... (initial state, OK)

First 5 known URLs:
  https://www.auto-selection.com/voiture-occasion/...
  ...
```

### 3. Premier vrai test avec dedup (limit 50)

```bash
python3 phase_a_scraper.py scrape auto-selection --limit 50
```

Au **premier run**, attendu :
```
yielded                 = 50
valid CarListing        = 50
inserted in Supabase    = ~5    ← uniquement les nouveautés
duplicate or invalid    = ~0
cross-source matched    = 0
```

Et dans le log : `[auto-selection] saved=90% GETs` 🎉

### 4. Voir les stats dedup

```bash
python3 dedup.py stats
```

### 5. Sweep des cars stale (à laisser tourner après quelques jours)

```bash
python3 dedup.py archive --dry-run --days 14
# Si ça affiche 50 cars à archiver, vérifier la liste, puis :
python3 dedup.py archive --days 14
```

---

## Ce que tu vas voir dans tes prochains scrapes

**Run 1 (juste après installation)** : 
- Premier scrape charge `known_urls` mais cache vide pour `content_hash` 
- Tous les GETs ont lieu (pas de gain L1, pas de gain L3 encore)
- L2 commence à matcher des doublons cross-source si t'en as

**Run 2 (le lendemain via cron)** :
- L1 skip ~95% des URLs (les nouvelles annonces sont rares)
- Gain massif : `~3 min au lieu de 1h`
- `dedup_stats` montre `saved=95%` GETs

**Run 7 (1 semaine après)** :
- L3 commence à kicker quand un dealer republie sans changement (annonces "expirées" relistées)
- Cross-source matches s'accumulent dans `cross_source_matches` table
- Tu peux requêter "quelle voiture est listée chez 2+ dealers" → potentiel arbitrage info

---

## Prochaines étapes (après validation)

1. ✅ **Phase A early dedup** — c'est ce qu'on vient de faire
2. **`cars_archive` table + auto-move** — quand cars sont en `status=expired` depuis >30j
3. **`price_history` table + tracking** — variation de prix observée à chaque re-scrape
4. **Cote AutoRadar** — calcul hebdo basé sur `price_history` agrégé

Mais d'abord, on valide ce qu'on vient de faire. Prends ton temps.
