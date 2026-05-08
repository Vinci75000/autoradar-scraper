#!/usr/bin/env python3
"""
apply_rivamedia_patch.py
═══════════════════════════════════════════════════════════════════════════
Intègre le module Rivamedia dans phase_a_scraper.py + scraper_sources.py.

Idempotent : safe à relancer (skip si patch déjà appliqué).
Atomique   : backup avant, rollback si erreur.

Modifications appliquées :

phase_a_scraper.py :
  P1 — import extract_rivamedia_rss
  P2 — dispatch elif rivamedia_rss dans scrape_listing (returns None)
  P3 — court-circuit RSS au début de scrape_all
  P4 — nouvelle méthode _scrape_rivamedia_rss
  P5 — 5 entrées PATCHES (gtcars + orleans ready, bourcier + code911 + lps deferred)

scraper_sources.py :
  S1 — enrichissement gtcars-prestige (domain, base_url, listings_url, lat/lng)
  S2 — enrichissement orleans-cars-shop
  S3 — enrichissement bourcier-auto-sport (domain only, deferred)
  S4 — enrichissement code-911 (domain only, deferred)
  S5 — note luxury-performance-selection (deferred, no website)

Usage:
    cd ~/Code/autoradar/scraper
    python apply_rivamedia_patch.py [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ─── Targets ─────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent
PHASE_A = REPO / "phase_a_scraper.py"
SOURCES_FILE = REPO / "scraper_sources.py"
EXTRACTOR = REPO / "extractors" / "extract_rivamedia.py"


# ─── Patch definitions for phase_a_scraper.py ────────────────────────

# P1 — Import after the existing extract_segond import
P1_FIND = "from extractors.extract_segond import extract_segond_listing"
P1_REPLACE = (
    "from extractors.extract_segond import extract_segond_listing\n"
    "from extractors.extract_rivamedia import extract_rivamedia_rss"
)
P1_MARKER = "from extractors.extract_rivamedia import extract_rivamedia_rss"

# P2 — Dispatch in scrape_listing : add elif rivamedia_rss right after custom_segond
P2_FIND = """        elif method == "custom_segond":
            car = extract_segond_listing(r.text, url)
        else:
            return None"""
P2_REPLACE = """        elif method == "custom_segond":
            car = extract_segond_listing(r.text, url)
        elif method == "rivamedia_rss":
            # RSS sources produce N items per fetch via scrape_all().
            # scrape_listing(url) is per-fiche extraction → not applicable.
            return None
        else:
            return None"""
P2_MARKER = "method == \"rivamedia_rss\":\n            # RSS sources produce N items per fetch"

# P3 — Short-circuit at start of scrape_all
P3_FIND = """    def scrape_all(self, *, limit=None, db=None):
        \"\"\"
        Discover URLs, scrape each, yield car dicts.
        If `db` provided: uses DedupCache for L1 (URL skip) + L3 (content hash skip).
        L2 (fingerprint cross-source) happens in caller after parsing.
        \"\"\"
        urls = self.discover_urls()"""
P3_REPLACE = """    def scrape_all(self, *, limit=None, db=None):
        \"\"\"
        Discover URLs, scrape each, yield car dicts.
        If `db` provided: uses DedupCache for L1 (URL skip) + L3 (content hash skip).
        L2 (fingerprint cross-source) happens in caller after parsing.
        \"\"\"
        # RSS feed dispatch: 1 fetch produces N items → bypass URL-by-URL discovery
        if self.cfg.get("extraction") == "rivamedia_rss":
            yield from self._scrape_rivamedia_rss(limit=limit, db=db)
            return

        urls = self.discover_urls()"""
P3_MARKER = "# RSS feed dispatch: 1 fetch produces N items"

# P4 — New method _scrape_rivamedia_rss inserted just before "# Selector sniffer" comment
P4_FIND = "                # L1 — URL already known: skip the GET entirely\n# Selector sniffer"
P4_REPLACE = '''                # L1 — URL already known: skip the GET entirely

    def _scrape_rivamedia_rss(self, *, limit=None, db=None):
        """
        RSS-based scraping: 1 fetch produces N items.
        Bypasses URL-by-URL discovery since the RSS already provides
        structured items. Hash content uses the `de` field as the
        signature (not raw HTML — RSS doesn't fetch fiche detail HTML).
        """
        rss_url = self.cfg.get("listings_url")
        if not rss_url:
            self.log.warning(f"[{self.slug}] no listings_url for rivamedia_rss")
            return

        source_name = self.cfg["display_name"]
        location = (self.cfg.get("city"), self.cfg.get("country") or "France")

        self.log.info(f"[rivamedia] fetching RSS for {self.slug}: {rss_url}")
        listings = extract_rivamedia_rss(rss_url, source_name, location)
        self.log.info(f"[rivamedia] {len(listings)} items returned by parser")

        cache = None
        if db is not None:
            cache = DedupCache(db, source_name, source_slug=self.slug)
            cache.load()

        rediscovered_urls = []
        yielded = 0

        try:
            for car in listings:
                if limit and yielded >= limit:
                    break

                url = car.get("src_url")
                if not url:
                    continue

                if cache:
                    cache.stats["urls_total"] += 1

                    # L1 — URL already known: skip
                    if cache.seen_url(url):
                        cache.stats["skipped_url"] += 1
                        rediscovered_urls.append(url)
                        continue

                    # L3 — content hash on the `de` field (structured signature)
                    content_hash = cache.hash_content(car.get("de") or "")
                    if cache.seen_content_hash(url, content_hash):
                        cache.stats["skipped_content"] += 1
                        rediscovered_urls.append(url)
                        continue
                    cache.stats["fetched"] += 1
                    car["_content_hash"] = content_hash
                    car["_dedup_cache"] = cache

                # Apply config defaults (mirrors scrape_listing post-processing)
                car["src"] = source_name
                if not car.get("ci"): car["ci"] = self.cfg.get("city") or ""
                if not car.get("co"): car["co"] = self.cfg.get("country") or "France"
                if not car.get("lat"): car["lat"] = self.cfg.get("lat")
                if not car.get("lng"): car["lng"] = self.cfg.get("lng")

                yield car
                yielded += 1
        finally:
            if cache and rediscovered_urls:
                try:
                    updated = cache.bump_seen_urls(rediscovered_urls)
                    self.log.info(f"bumped last_seen_at on {updated} re-encountered URLs")
                except Exception as e:
                    self.log.warning(f"bump_seen_urls failed: {e}")
            if cache:
                try:
                    cache.flush_stats()
                    self.log.info(cache.summary())
                except Exception as e:
                    self.log.error(f"flush_stats failed: {e}")


# Selector sniffer'''
P4_MARKER = "def _scrape_rivamedia_rss(self,"

# P5 — 5 PATCHES entries inserted just before "car-legendary-monaco"
P5_FIND = '''    "car-legendary-monaco": {
        "listings_url":     "https://carlegendary.com/nos-vehicules-haut-de-gamme/",'''
P5_REPLACE = '''    "gtcars-prestige": {
        "listings_url":     "https://www.gtcarsprestige.com/rss/annonces.xml",
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      r"/annonce-[a-z0-9-]+-\\d+/?$",
        "extraction":       "rivamedia_rss",
        "selectors":        {},
        "status":           "ready",
        "notes_recon":      "Plateforme white-label Rivamedia (CDN auto.cdn-rivamedia.com). Flux RSS expose: 145 items observes 8/5/26. Module extract_rivamedia.py parse XML standardise (preambule CSV [Boite, ch, km, MM/YYYY, garantie?, couleur?, condition] + CDATA HTML). 1 fetch = N cars (scalable North Star). Stock Bugatti/Pagani/McLaren/Aston/Ferrari/Lambo premium.",
    },
    "orleans-cars-shop": {
        "listings_url":     "https://www.orleans-cars-shop.fr/rss/annonces.xml",
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      r"/annonce-[a-z0-9-]+-\\d+/?$",
        "extraction":       "rivamedia_rss",
        "selectors":        {},
        "status":           "ready",
        "notes_recon":      "Plateforme Rivamedia (meme stack que gtcars-prestige). Flux RSS: 68 items observes 8/5/26. Multi-marques generaliste premium (Skoda, Alfa, VW, etc.). Couleur souvent presente dans le preambule (vs gtcars qui ne l'expose pas).",
    },
    "bourcier-auto-sport": {
        "listings_url":     None,
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      None,
        "extraction":       "manual",
        "selectors":        {},
        "status":           "deferred-domain-broken",
        "notes_recon":      "DOMAIN BROKEN au 8/5/26 — bourcierautosport.com retourne HTTP 000 sur tous paths (rss, feed, sitemap, annonces, marques, occasion, voitures, stock). DNS ou TLS cassé. Probablement meme stack Rivamedia qu'gtcars (titles partages, payload home identique md5) mais infrastructure morte. Reprobe trimestriellement.",
    },
    "code-911": {
        "listings_url":     None,
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      None,
        "extraction":       "manual",
        "selectors":        {},
        "status":           "deferred-wix-spa",
        "notes_recon":      "Site Wix 100% SPA (rendu cote client). curl + UA navigateur retourne wixErrorPagesApp shell pour /annonce, /sitemap.xml, fiche detail. ~20 cars Porsche estimes. Necessite Playwright stealth pour rendu JS — ROI faible vs invest infra. Defer jusqu'a sprint Playwright dedie.",
    },
    "luxury-performance-selection": {
        "listings_url":     None,
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      None,
        "extraction":       "manual",
        "selectors":        {},
        "status":           "deferred-no-website",
        "notes_recon":      "Pas de site web propre identifie. Vend exclusivement via LBC/La Centrale/AutoScout24/auto-selection.com. Stock indirectement capte via auto-selection (deja active). Phase B partnership envisageable.",
    },
    "car-legendary-monaco": {
        "listings_url":     "https://carlegendary.com/nos-vehicules-haut-de-gamme/",'''
P5_MARKER = '"gtcars-prestige": {\n        "listings_url":     "https://www.gtcarsprestige.com/rss/annonces.xml"'


# ─── Patch definitions for scraper_sources.py ────────────────────────

# S1 — gtcars-prestige enrichment
S1_FIND = '''    "gtcars-prestige": {
        "slug": "gtcars-prestige",
        "display_name": "GTcars Prestige",
        "country": "France", "city": "Sainte-Genevieve-des-Bois",
        "tier": 1, "type": "dealer",'''
S1_REPLACE = '''    "gtcars-prestige": {
        "slug": "gtcars-prestige",
        "display_name": "GTcars Prestige",
        "domain": "gtcarsprestige.com",
        "base_url": "https://www.gtcarsprestige.com",
        "listings_url": "https://www.gtcarsprestige.com/rss/annonces.xml",
        "sitemap_url": None,
        "country": "France", "city": "Sainte-Geneviève-des-Bois",
        "lat": 48.6333, "lng": 2.3333,
        "tier": 1, "type": "dealer",'''
S1_MARKER = '"listings_url": "https://www.gtcarsprestige.com/rss/annonces.xml"'

# S2 — orleans-cars-shop enrichment
S2_FIND = '''    "orleans-cars-shop": {
        "slug": "orleans-cars-shop",
        "display_name": "Orleans Cars Shop",
        "country": "France", "city": "Ingre",
        "tier": 2, "type": "dealer",'''
S2_REPLACE = '''    "orleans-cars-shop": {
        "slug": "orleans-cars-shop",
        "display_name": "Orleans Cars Shop",
        "domain": "orleans-cars-shop.fr",
        "base_url": "https://www.orleans-cars-shop.fr",
        "listings_url": "https://www.orleans-cars-shop.fr/rss/annonces.xml",
        "sitemap_url": None,
        "country": "France", "city": "Ingré",
        "lat": 47.9128, "lng": 1.8333,
        "tier": 2, "type": "dealer",'''
S2_MARKER = '"listings_url": "https://www.orleans-cars-shop.fr/rss/annonces.xml"'

# S3 — bourcier-auto-sport enrichment (deferred-domain-broken)
S3_FIND = '''    "bourcier-auto-sport": {
        "slug": "bourcier-auto-sport",
        "display_name": "Bourcier Auto Sport",
        "country": "France", "city": "Saint-Barthelemy-d'Anjou",
        "tier": 2, "type": "dealer",'''
S3_REPLACE = '''    "bourcier-auto-sport": {
        "slug": "bourcier-auto-sport",
        "display_name": "Bourcier Auto Sport",
        "domain": "bourcierautosport.com",
        "base_url": "https://www.bourcierautosport.com",
        "listings_url": None,
        "sitemap_url": None,
        "country": "France", "city": "Saint-Barthélemy-d'Anjou",
        "lat": 47.4667, "lng": -0.4833,
        "tier": 2, "type": "dealer",'''
S3_MARKER = '"domain": "bourcierautosport.com"'

# S4 — code-911 enrichment (deferred-wix-spa)
S4_FIND = '''    "code-911": {
        "slug": "code-911",
        "display_name": "Code 911 Sport & Prestige",
        "country": "France", "city": "La Chapelle-des-Fougeretz",
        "tier": 2, "type": "dealer",'''
S4_REPLACE = '''    "code-911": {
        "slug": "code-911",
        "display_name": "Code 911 Sport & Prestige",
        "domain": "code911.fr",
        "base_url": "https://www.code911.fr",
        "listings_url": None,
        "sitemap_url": None,
        "country": "France", "city": "La Chapelle-des-Fougeretz",
        "lat": 48.1500, "lng": -1.6833,
        "tier": 2, "type": "dealer",'''
S4_MARKER = '"domain": "code911.fr"'

# S5 — luxury-performance-selection (deferred-no-website, lat/lng Antibes)
S5_FIND = '''    "luxury-performance-selection": {
        "slug": "luxury-performance-selection",
        "display_name": "Luxury & Performance Selection",
        "country": "France", "city": "Antibes",
        "tier": 1, "type": "dealer",'''
S5_REPLACE = '''    "luxury-performance-selection": {
        "slug": "luxury-performance-selection",
        "display_name": "Luxury & Performance Selection",
        "domain": None,
        "base_url": None,
        "listings_url": None,
        "sitemap_url": None,
        "country": "France", "city": "Antibes",
        "lat": 43.5847, "lng": 7.1235,
        "tier": 1, "type": "dealer",'''
S5_MARKER = '"display_name": "Luxury & Performance Selection",\n        "domain": None'


# ─── Helpers ────────────────────────────────────────────────────────


def log(msg, level="INFO"):
    icons = {"INFO": "·", "OK": "✓", "SKIP": "→", "WARN": "!", "ERR": "✗"}
    print(f"  {icons.get(level, '·')} {msg}")


def apply_patch(file_path: Path, find: str, replace: str, marker: str,
                label: str, dry_run: bool) -> str:
    """
    Idempotent str_replace. Returns 'ok' | 'skip' | 'fail' | 'dry'.
    'skip' if marker already present.
    'fail' raises ValueError (caller handles rollback).
    """
    content = file_path.read_text(encoding="utf-8")

    if marker in content:
        log(f"{label}: marker already present (idempotent skip)", "SKIP")
        return "skip"

    if find not in content:
        raise ValueError(
            f"{label}: anchor not found in {file_path.name}.\n"
            f"  Expected near: {find[:80]!r}..."
        )

    if content.count(find) > 1:
        raise ValueError(
            f"{label}: anchor not unique in {file_path.name} "
            f"({content.count(find)} matches)."
        )

    if dry_run:
        log(f"{label}: would patch ({len(find)} → {len(replace)} chars)", "INFO")
        return "dry"

    new_content = content.replace(find, replace)
    file_path.write_text(new_content, encoding="utf-8")
    log(f"{label}: applied", "OK")
    return "ok"


def verify_python_syntax(file_path: Path) -> None:
    """Compile-check via py_compile. Raises on syntax error."""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(file_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SyntaxError(
            f"py_compile failed on {file_path.name}:\n{result.stderr}"
        )


def verify_imports() -> None:
    """Import test that exercises the patched modules."""
    cmd = [
        sys.executable, "-c",
        "from extractors.extract_rivamedia import extract_rivamedia_rss; "
        "import phase_a_scraper as p; "
        "import scraper_sources as s; "
        "assert 'gtcars-prestige' in p.SOURCES, 'gtcars not in merged SOURCES'; "
        "assert p.SOURCES['gtcars-prestige'].get('extraction') == 'rivamedia_rss', "
        "  f'wrong extraction: {p.SOURCES[\"gtcars-prestige\"].get(\"extraction\")}'; "
        "assert p.SOURCES['gtcars-prestige'].get('lat') == 48.6333, "
        "  f'wrong lat: {p.SOURCES[\"gtcars-prestige\"].get(\"lat\")}'; "
        "assert p.SOURCES['orleans-cars-shop'].get('extraction') == 'rivamedia_rss'; "
        "assert p.SOURCES['code-911'].get('status') == 'deferred-wix-spa'; "
        "assert p.SOURCES['bourcier-auto-sport'].get('status') == 'deferred-domain-broken'; "
        "print('  ✓ all imports + dispatch checks OK')"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    if result.returncode != 0:
        raise RuntimeError(
            f"Import/dispatch verification failed:\n"
            f"  stdout: {result.stdout}\n  stderr: {result.stderr}"
        )
    print(result.stdout, end="")


# ─── Main ───────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Apply Rivamedia integration patch")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing files")
    args = parser.parse_args()

    print("═══════════════════════════════════════════════════════════")
    print("  apply_rivamedia_patch.py")
    print(f"  cwd: {REPO}")
    print(f"  mode: {'DRY-RUN' if args.dry_run else 'APPLY'}")
    print("═══════════════════════════════════════════════════════════\n")

    # ─── Pre-checks ──────────────────────────────────────────────
    print("[0/4] Pre-checks")
    for f in [PHASE_A, SOURCES_FILE, EXTRACTOR]:
        if not f.exists():
            log(f"MISSING: {f}", "ERR")
            sys.exit(1)
        log(f"present: {f.name}", "OK")
    print()

    # ─── Backup ──────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups = []
    if not args.dry_run:
        print("[1/4] Backup")
        for f in [PHASE_A, SOURCES_FILE]:
            bak = f.with_suffix(f.suffix + f".bak_rivamedia_{timestamp}")
            shutil.copy2(f, bak)
            backups.append((f, bak))
            log(f"{f.name} → {bak.name}", "OK")
        print()
    else:
        print("[1/4] Backup (dry-run, skipped)\n")

    try:
        # ─── Patch phase_a_scraper.py ─────────────────────────────
        print("[2/4] Patch phase_a_scraper.py")
        apply_patch(PHASE_A, P1_FIND, P1_REPLACE, P1_MARKER,
                    "P1 import extract_rivamedia_rss", args.dry_run)
        apply_patch(PHASE_A, P2_FIND, P2_REPLACE, P2_MARKER,
                    "P2 dispatch scrape_listing", args.dry_run)
        apply_patch(PHASE_A, P3_FIND, P3_REPLACE, P3_MARKER,
                    "P3 short-circuit scrape_all", args.dry_run)
        apply_patch(PHASE_A, P4_FIND, P4_REPLACE, P4_MARKER,
                    "P4 method _scrape_rivamedia_rss", args.dry_run)
        apply_patch(PHASE_A, P5_FIND, P5_REPLACE, P5_MARKER,
                    "P5 5 PATCHES entries (gtcars + 4)", args.dry_run)
        print()

        # ─── Patch scraper_sources.py ────────────────────────────
        print("[3/4] Patch scraper_sources.py")
        apply_patch(SOURCES_FILE, S1_FIND, S1_REPLACE, S1_MARKER,
                    "S1 gtcars-prestige enrichment", args.dry_run)
        apply_patch(SOURCES_FILE, S2_FIND, S2_REPLACE, S2_MARKER,
                    "S2 orleans-cars-shop enrichment", args.dry_run)
        apply_patch(SOURCES_FILE, S3_FIND, S3_REPLACE, S3_MARKER,
                    "S3 bourcier-auto-sport enrichment", args.dry_run)
        apply_patch(SOURCES_FILE, S4_FIND, S4_REPLACE, S4_MARKER,
                    "S4 code-911 enrichment", args.dry_run)
        apply_patch(SOURCES_FILE, S5_FIND, S5_REPLACE, S5_MARKER,
                    "S5 luxury-performance-selection enrichment", args.dry_run)
        print()

        # ─── Verify ──────────────────────────────────────────────
        if not args.dry_run:
            print("[4/4] Verify")
            verify_python_syntax(PHASE_A)
            log("py_compile phase_a_scraper.py OK", "OK")
            verify_python_syntax(SOURCES_FILE)
            log("py_compile scraper_sources.py OK", "OK")
            verify_imports()
            print()

        # ─── Done ────────────────────────────────────────────────
        print("═══════════════════════════════════════════════════════════")
        if args.dry_run:
            print("  DRY-RUN OK — re-run without --dry-run to apply")
        else:
            print("  PATCH APPLIED")
            print(f"  Backups: {[b[1].name for b in backups]}")
            print()
            print("  Next steps:")
            print("    python phase_a_scraper.py status | grep -E '(gtcars|orleans|bourcier|code-911|luxury)'")
            print("    python phase_a_scraper.py scrape gtcars-prestige --limit 5")
        print("═══════════════════════════════════════════════════════════")

    except Exception as e:
        print()
        print("═══════════════════════════════════════════════════════════")
        log(f"PATCH FAILED: {e}", "ERR")
        if not args.dry_run and backups:
            print()
            log("Rolling back from backups...", "WARN")
            for original, bak in backups:
                shutil.copy2(bak, original)
                log(f"restored {original.name}", "OK")
        print("═══════════════════════════════════════════════════════════")
        sys.exit(1)


if __name__ == "__main__":
    main()
