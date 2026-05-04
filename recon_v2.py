"""
AutoRadar — recon_v2.py
═══════════════════════════════════════════════════════════════════════════
Deeper recon after the first pass revealed that:
  - Most `listings_url` guesses returned 404 (the URL pattern guessed was wrong)
  - Most sitemaps work BUT some are sitemap-INDEXES pointing to sub-sitemaps
  - 4 sites returned "no-sitemap" at /sitemap.xml — try alternate paths

This script does 3 things per source:
  1. SITEMAP DEEP DIVE
     - Try /sitemap.xml, /sitemap_index.xml, /wp-sitemap.xml, /sitemap-index.xml
     - If response is a sitemap-index (<sitemapindex>), follow each sub-sitemap
     - Collect ALL final URLs that look like vehicle listings
  2. ALTERNATE LISTING PATHS
     - Try /stock/, /occasion/, /catalogue/, /annonces/, /nos-vehicules/, etc.
  3. SAMPLE A REAL LISTING
     - Fetch one URL that looks like a listing, dump JSON-LD types
     - Confirms whether scraping = JSON-LD parse (easy) or HTML selectors (work)

Usage from autoradar-scraper directory:
    python3 recon_v2.py                         # all sources
    python3 recon_v2.py motors-corner           # one source
    python3 recon_v2.py --json > recon_v2.json  # save full data

Run time: ~3-5 min for all 22 sources (rate-limited 2s between requests).
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import sys
import time
import json
import re
from urllib.parse import urlparse, urljoin
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from scraper_sources import SOURCES


# ─── Constants ──────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                   "Version/17.5 Safari/605.1.15"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# Sitemap candidate paths (in priority order)
SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",       # Yoast SEO default
    "/wp-sitemap.xml",          # WordPress 5.5+ native
    "/sitemap-index.xml",       # some CMS
    "/sitemap1.xml",
]

# Listing-page candidate paths
LISTING_PATHS = [
    "/vehicules/", "/vehicules", "/voitures/", "/voitures",
    "/stock/", "/stock", "/stock-vehicules/",
    "/occasion/", "/occasions/", "/vehicule-occasion/",
    "/nos-vehicules/", "/nos-voitures/",
    "/catalogue/", "/annonces/", "/inventaire/",
    "/voitures-en-vente/", "/voitures-a-vendre/",
    "/voitures-de-collection/", "/voiture-occasion/",
    "/automobiles-en-vente/", "/cars/", "/car/",
]

# URL patterns that suggest a single-vehicle listing page
LISTING_URL_PATTERNS = [
    r"/vehicule[s]?/", r"/voiture[s]?/", r"/auto[s]?/",
    r"/stock/", r"/annonce[s]?/", r"/cars?/", r"/inventaire/",
    r"-a-vendre", r"-occasion", r"/produit[s]?/", r"/product[s]?/",
]
LISTING_URL_RE = re.compile("|".join(LISTING_URL_PATTERNS), re.I)

TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 1.5  # seconds


# ─── HTTP helper ────────────────────────────────────────────────────────────
def _get(client: httpx.Client, url: str) -> Optional[httpx.Response]:
    """GET with built-in error handling. Returns None on failure."""
    try:
        r = client.get(url)
        return r
    except (httpx.HTTPError, httpx.RequestError):
        return None


# ─── Sitemap deep dive ──────────────────────────────────────────────────────
def discover_sitemap(client: httpx.Client, base_url: str) -> dict:
    """
    Probe all SITEMAP_PATHS and return the first one that responds 200.
    If the response is a sitemap-INDEX, recurse one level and merge URLs.
    Returns: {'sitemap_url': str|None, 'all_urls': list[str], 'is_index': bool}
    """
    out = {"sitemap_url": None, "all_urls": [], "is_index": False, "tried": []}

    for path in SITEMAP_PATHS:
        url = base_url.rstrip("/") + path
        r = _get(client, url)
        out["tried"].append({"url": url, "status": r.status_code if r else "err"})
        if r is None or r.status_code != 200:
            continue
        if "<urlset" not in r.text and "<sitemapindex" not in r.text:
            continue  # not actually a sitemap
        out["sitemap_url"] = url

        # Sitemap index → follow sub-sitemaps
        if "<sitemapindex" in r.text:
            out["is_index"] = True
            sub_urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
            for sub_url in sub_urls[:10]:  # cap to 10 sub-sitemaps
                time.sleep(SLEEP_BETWEEN_REQUESTS)
                sr = _get(client, sub_url.strip())
                if sr and sr.status_code == 200:
                    out["all_urls"].extend(re.findall(r"<loc>([^<]+)</loc>", sr.text))
        else:
            # Plain sitemap
            out["all_urls"] = re.findall(r"<loc>([^<]+)</loc>", r.text)

        break  # stop at first working sitemap

    return out


# ─── Listing path discovery ─────────────────────────────────────────────────
def discover_listings_url(client: httpx.Client, base_url: str) -> dict:
    """Try alternate paths until we get a 200 with HTML that looks like inventory."""
    out = {"working_url": None, "tried": [], "candidates_with_200": []}

    for path in LISTING_PATHS:
        url = base_url.rstrip("/") + path
        r = _get(client, url)
        status = r.status_code if r else "err"
        out["tried"].append({"url": url, "status": status})
        if r is None or r.status_code != 200:
            continue
        # Heuristic: page should contain multiple links matching listing patterns
        anchor_hrefs = re.findall(r'<a[^>]+href="([^"]+)"', r.text)
        listing_count = sum(1 for h in anchor_hrefs if LISTING_URL_RE.search(h))
        out["candidates_with_200"].append({
            "url": url,
            "listing_links_found": listing_count,
            "page_size_kb": round(len(r.content) / 1024, 1),
        })
        if listing_count >= 3 and out["working_url"] is None:
            out["working_url"] = url
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    return out


# ─── Homepage nav extraction ────────────────────────────────────────────────
def extract_inventory_link_from_homepage(client: httpx.Client, base_url: str) -> Optional[str]:
    """Fetch the homepage and find the most likely inventory link from nav."""
    r = _get(client, base_url)
    if r is None or r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    keywords = ("vehicule", "voiture", "stock", "occasion", "annonce", "catalogue", "inventaire")

    best = None
    best_score = 0
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = a["href"].lower()
        score = 0
        for kw in keywords:
            if kw in href:
                score += 2
            if kw in text:
                score += 1
        # de-prioritize blog/news links
        if any(b in href for b in ("/blog/", "/actualite", "/news")):
            score -= 3
        if score > best_score:
            best_score = score
            best = a["href"]

    if best is None:
        return None
    if best.startswith("http"):
        return best
    return urljoin(base_url, best)


# ─── Listing sample (the money question: JSON-LD or not) ────────────────────
def sample_listing(client: httpx.Client, listing_url: str) -> dict:
    """Fetch one detail page and report what data is exposed."""
    out = {"url": listing_url, "status": None, "json_ld_types": [],
           "has_vehicle_jsonld": False, "title": "", "h1": "", "size_kb": 0}
    r = _get(client, listing_url)
    if r is None:
        out["status"] = "err"
        return out
    out["status"] = r.status_code
    out["size_kb"] = round(len(r.content) / 1024, 1)
    if r.status_code != 200:
        return out

    soup = BeautifulSoup(r.text, "html.parser")
    out["title"] = (soup.title.get_text(strip=True) if soup.title else "")[:100]
    h1 = soup.find("h1")
    out["h1"] = (h1.get_text(strip=True) if h1 else "")[:100]

    # JSON-LD scan
    types = []
    for s in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(s.string or "{}")
            if isinstance(data, dict):
                if data.get("@type"):
                    types.append(data["@type"])
                for d in data.get("@graph", []):
                    if isinstance(d, dict) and d.get("@type"):
                        types.append(d["@type"])
            elif isinstance(data, list):
                for d in data:
                    if isinstance(d, dict) and d.get("@type"):
                        types.append(d["@type"])
        except Exception:
            pass
    out["json_ld_types"] = sorted(set(types))
    out["has_vehicle_jsonld"] = any(
        t in types for t in ("Car", "Vehicle", "Product", "Offer")
    )
    return out


# ─── Pick a sample listing URL from a list ──────────────────────────────────
def pick_listing_url(urls: list[str]) -> Optional[str]:
    """From a list of URLs (from sitemap), pick one that looks like a vehicle listing."""
    candidates = [u for u in urls if LISTING_URL_RE.search(u)]
    # Prefer URLs deeper in the path (more specific = more likely a detail page)
    candidates.sort(key=lambda u: u.count("/"), reverse=True)
    # Avoid pagination URLs
    candidates = [u for u in candidates if not re.search(r"page[/=-]\d+|/p\d+/", u, re.I)]
    return candidates[0] if candidates else None


# ─── Per-source full recon ──────────────────────────────────────────────────
def deep_recon(slug: str, *, verbose: bool = True) -> dict:
    cfg = SOURCES[slug]
    report = {
        "slug": slug,
        "display_name": cfg["display_name"],
        "base_url": cfg["base_url"],
        "original_listings_url": cfg["listings_url"],
        "original_listings_status": None,
    }

    if verbose:
        print(f"\n[{slug}] {cfg['display_name']}")
        print(f"  base: {cfg['base_url']}")

    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        # 1. Re-test original listings URL
        r = _get(client, cfg["listings_url"])
        report["original_listings_status"] = r.status_code if r else "err"
        if verbose:
            print(f"  original listings_url ({cfg['listings_url']}): {report['original_listings_status']}")

        # 2. Sitemap deep dive
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        sm = discover_sitemap(client, cfg["base_url"])
        report["sitemap"] = sm
        listing_urls = [u for u in sm["all_urls"] if LISTING_URL_RE.search(u)]
        report["sitemap_listing_url_count"] = len(listing_urls)
        if verbose:
            tag = "INDEX" if sm["is_index"] else "PLAIN"
            print(f"  sitemap: {sm['sitemap_url']} [{tag}] — {len(sm['all_urls'])} total URLs, "
                  f"{len(listing_urls)} look like listings")

        # 3. Homepage nav extraction
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        nav_link = extract_inventory_link_from_homepage(client, cfg["base_url"])
        report["homepage_nav_link"] = nav_link
        if verbose and nav_link:
            print(f"  homepage nav -> {nav_link}")

        # 4. Listing path probe (only if we don't already have a working URL)
        already_works = (report["original_listings_status"] == 200)
        if not already_works:
            paths = discover_listings_url(client, cfg["base_url"])
            report["listing_path_probe"] = paths
            if verbose and paths["working_url"]:
                print(f"  found working listing path: {paths['working_url']}")
            elif verbose:
                cands = [p for p in paths["tried"] if p["status"] == 200]
                if cands:
                    print(f"  no path with ≥3 listing links, but {len(cands)} returned 200")

        # 5. Sample one listing detail page
        sample_url = pick_listing_url(listing_urls)
        if sample_url:
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            sample = sample_listing(client, sample_url)
            report["sample"] = sample
            if verbose:
                ld = "📋 JSON-LD" if sample["has_vehicle_jsonld"] else "         "
                print(f"  sample: {sample_url}")
                print(f"    -> {ld} types={sample['json_ld_types']} title='{sample['title'][:60]}'")

    # Final recommendation
    rec = recommend(report)
    report["recommendation"] = rec
    if verbose:
        print(f"  ★ RECOMMENDATION: {rec['strategy']} — {rec['reason']}")

    return report


# ─── Final per-source recommendation ────────────────────────────────────────
def recommend(report: dict) -> dict:
    sm = report.get("sitemap", {})
    listings = report.get("sitemap_listing_url_count", 0)
    sample = report.get("sample", {})
    nav = report.get("homepage_nav_link")
    probe = report.get("listing_path_probe", {})

    # Best case: sitemap with listings + JSON-LD on sample
    if listings >= 3 and sample.get("has_vehicle_jsonld"):
        return {
            "group": "A",
            "strategy": "sitemap+jsonld",
            "reason": f"{listings} listings in sitemap + JSON-LD on detail pages",
            "scrape_method": "sitemap_jsonld",
        }

    # Great case: sitemap with listings, no JSON-LD but workable HTML
    if listings >= 3:
        return {
            "group": "B",
            "strategy": "sitemap+selectors",
            "reason": f"{listings} listings in sitemap, no JSON-LD — needs CSS selectors",
            "scrape_method": "httpx_bs4",
        }

    # OK case: working listings page found, can crawl from there
    if probe.get("working_url"):
        return {
            "group": "B",
            "strategy": "crawl-from-listings-page",
            "reason": f"listings page found: {probe['working_url']}",
            "scrape_method": "httpx_bs4",
        }

    # Fallback: homepage nav points somewhere usable
    if nav:
        return {
            "group": "C",
            "strategy": "manual-inspect",
            "reason": f"nav link suggests {nav} — manual selectors needed",
            "scrape_method": "httpx_bs4",
        }

    # Worst: nothing automatic worked
    return {
        "group": "D",
        "strategy": "deferred-or-manual",
        "reason": "no sitemap, no working listings path, no nav link — manual or skip",
        "scrape_method": "deferred",
    }


# ─── Bulk run ───────────────────────────────────────────────────────────────
def run_all(*, verbose: bool = True) -> list[dict]:
    reports = []
    for slug in SOURCES:
        try:
            r = deep_recon(slug, verbose=verbose)
            reports.append(r)
        except Exception as e:
            if verbose:
                print(f"\n[{slug}] ERROR: {e}")
            reports.append({"slug": slug, "error": str(e)})
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    # Summary
    if verbose:
        print("\n" + "=" * 75)
        print("SUMMARY")
        print("=" * 75)
        groups = {"A": [], "B": [], "C": [], "D": []}
        for r in reports:
            rec = r.get("recommendation", {})
            g = rec.get("group", "D")
            groups[g].append(f"{r['slug']:30s} {rec.get('reason','')}")
        for g, label in [("A", "READY (sitemap + JSON-LD, ~30min/dealer)"),
                         ("B", "READY (sitemap or listings page, selectors needed, ~1h/dealer)"),
                         ("C", "MANUAL (nav link found, ~2h/dealer)"),
                         ("D", "DEFERRED (no automatic path)")]:
            print(f"\n  Group {g} — {label}: {len(groups[g])} sources")
            for line in groups[g]:
                print(f"    {line}")
    return reports


# ─── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    json_out = "--json" in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        slug = args[0]
        if slug not in SOURCES:
            print(f"unknown source: {slug}")
            print(f"available: {', '.join(SOURCES.keys())}")
            sys.exit(1)
        r = deep_recon(slug, verbose=not json_out)
        if json_out:
            print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        reports = run_all(verbose=not json_out)
        if json_out:
            print(json.dumps(reports, indent=2, ensure_ascii=False))
