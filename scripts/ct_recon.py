"""Quick recon script for classic-trader.com.

Run from repo root:
    python -u scripts/ct_recon.py

Output:
  - HTTP status + sitemap discovery
  - 1 listing sample HTML saved to /tmp/ct_sample.html
  - DOM pattern counts (JSON-LD, microdata, dt/dd, field-*, etc.)
  - Key field contexts (price, mileage, year, location)
"""
from __future__ import annotations

import re

import httpx

BASE = "https://classic-trader.com"
HOMEPAGE = f"{BASE}/de/automobile"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ─── 1. Homepage / listings ────────────────────────────────────────────────
section("1) HOMEPAGE / LISTINGS")
r = httpx.get(HOMEPAGE, headers=HEADERS, follow_redirects=True, timeout=30.0)
print(f"  URL final: {r.url}")
print(f"  Status: {r.status_code}")
print(f"  Length: {len(r.text)} bytes")
print(f"  Server: {r.headers.get('server', 'n/a')}")
print(f"  Set-Cookie: {bool(r.headers.get('set-cookie'))}")

# Look for next/prev pagination, "cars" count, etc.
m = re.search(r"(\d+[\s.,]*\d*)\s*(?:Fahrzeuge|cars|vehicles|véhicules|annonces)", r.text)
if m:
    print(f"  Visible stock count: {m.group(0)}")


# ─── 2. Sitemap discovery ──────────────────────────────────────────────────
section("2) SITEMAP DISCOVERY")
for sm_url in [
    f"{BASE}/sitemap.xml",
    f"{BASE}/sitemap_index.xml",
    f"{BASE}/sitemaps.xml",
    f"{BASE}/de/sitemap.xml",
]:
    try:
        rs = httpx.get(sm_url, headers=HEADERS, follow_redirects=True, timeout=15.0)
        print(f"  {sm_url} → {rs.status_code} ({len(rs.text)}B)")
        if rs.status_code == 200 and ("<urlset" in rs.text or "<sitemapindex" in rs.text):
            if "<sitemapindex" in rs.text:
                subs = re.findall(r"<sitemap>\s*<loc>([^<]+)</loc>", rs.text)
                print(f"    → sitemapindex with {len(subs)} sub-sitemaps")
                for s in subs[:5]:
                    print(f"      • {s}")
            else:
                urls = re.findall(r"<loc>([^<]+)</loc>", rs.text)
                print(f"    → urlset with {len(urls)} URLs")
                for u in urls[:5]:
                    print(f"      • {u}")
            break
    except Exception as e:
        print(f"  {sm_url} → ERROR {e}")


# ─── 3. Find one listing URL ────────────────────────────────────────────────
section("3) FIND A LISTING URL")
listing_patterns = [
    r'href="(/de/automobile/\d+[^"]*)"',
    r'href="(/de/[^"/]+/automobile/\d+[^"]*)"',
    r'href="(/de/(?:fahrzeug|annonce|car|vehicle)/\d+[^"]*)"',
    r'href="(/de/automobile/[a-z0-9-]+-\d+)"',
    r'href="(https://classic-trader\.com/de/[^"]+/\d+[^"]*)"',
]
found_links = []
for pat in listing_patterns:
    matches = re.findall(pat, r.text)
    if matches:
        print(f"  pattern {pat!r:50} → {len(matches)} matches")
        for m in matches[:3]:
            found_links.append(m if m.startswith("http") else BASE + m)
            print(f"    • {m}")
if not found_links:
    print("  No listings found — try alternative patterns")
    # broad: any /de/X/Y/numericid
    for m in re.findall(r'href="(/de/[^"]+/\d{5,})"', r.text)[:5]:
        print(f"    broad: {m}")
        found_links.append(BASE + m)


# ─── 4. Sample one listing ──────────────────────────────────────────────────
if found_links:
    sample_url = found_links[0]
    section(f"4) SAMPLE LISTING: {sample_url}")
    try:
        rd = httpx.get(sample_url, headers=HEADERS, follow_redirects=True, timeout=30.0)
        print(f"  Status: {rd.status_code}")
        print(f"  Length: {len(rd.text)} bytes")
        with open("/tmp/ct_sample.html", "w") as f:
            f.write(rd.text)
        print("  Saved to /tmp/ct_sample.html")

        text = rd.text
        patterns = [
            ("JSON-LD scripts", r'<script[^>]*type="application/ld\+json"'),
            ("itemprop attrs", r'itemprop="[^"]+"'),
            ("itemtype attrs", r'itemtype="[^"]+"'),
            ("og:price", r'property="(?:og:)?price[^"]*"\s*content="[^"]+"'),
            ("og:image", r'property="og:image"\s*content="[^"]+"'),
            ("dt tags", r"<dt\b"),
            ("dd tags", r"<dd\b"),
            ("dl tags", r"<dl\b"),
            ("field-name- divs", r'class="[^"]*field-name-[^"]*"'),
            ("data-attribute price", r'data-(?:price|amount|value)="[^"]+"'),
            ("h1", r"<h1[^>]*>([^<]{5,200})</h1>"),
            ("h2", r"<h2[^>]*>([^<]{5,150})</h2>"),
            ("Mileage / Kilometer ctx", r".{30}(?:Kilometer|Mileage|km)\b.{200}"),
            ("Baujahr/Year ctx", r".{30}(?:Baujahr|Year of manufacture)\b.{150}"),
            ("Preis/Price ctx", r".{30}(?:Preis|Price|EUR|€)\s*[\d.,\s]{4,}.{100}"),
            ("Standort/Location ctx", r".{30}(?:Standort|Location|City)\b.{150}"),
            ("Kraftstoff/Fuel ctx", r".{30}(?:Kraftstoff|Fuel)\b.{150}"),
            ("Getriebe/Gearbox ctx", r".{30}(?:Getriebe|Gearbox|Transmission)\b.{150}"),
        ]
        for name, p in patterns:
            ms = re.findall(p, text, re.DOTALL)
            print(f"\n  === {name} ===  count: {len(ms)}")
            for x in ms[:2]:
                snip = x if isinstance(x, str) else (x[0] if x else "")
                print(f"    {repr(snip)[:280]}")
    except Exception as e:
        print(f"  ERROR fetching listing: {e}")
else:
    print("\n  ⚠ No listing URL found from homepage. Manual inspection needed.")
