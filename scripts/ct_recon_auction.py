"""Auction-specific DOM recon on /tmp/ct_sample.html (Mercedes 420 SL).

Identifies how classic-trader exposes:
  - estimate_low / estimate_high
  - bid_current
  - bid_count
  - reserve_met
  - closes_at / started_at
  - watchers
  - lot_number
  - status (live / upcoming / sold)

Also dumps ALL <dt>/<dd> pairs (40 expected) — for car specs (mk/mo/yr/km).
"""
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def section(t: str) -> None:
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


html = Path("/tmp/ct_sample.html").read_text()
soup = BeautifulSoup(html, "html.parser")

# ─── 1. JSON-LD payload (full dump) ────────────────────────────────────────
section("1) JSON-LD blocks (parsed)")
for i, m in enumerate(re.finditer(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    html, re.DOTALL,
), 1):
    try:
        data = json.loads(m.group(1))
        print(f"\n--- block #{i} ---")
        if isinstance(data, list):
            for item in data:
                print(f"  @type: {item.get('@type')}")
                print(f"  name: {item.get('name', '')[:100]}")
                print(f"  keys: {list(item.keys())}")
        else:
            print(f"  @type: {data.get('@type')}")
            print(f"  keys: {list(data.keys())}")
    except Exception as e:
        print(f"  parse err: {e}")


# ─── 2. <dt>/<dd> pairs — car specs ────────────────────────────────────────
section("2) ALL <dt><dd> PAIRS (specs structure)")
all_pairs = []
for dl in soup.find_all("dl"):
    pairs = list(zip(dl.find_all("dt"), dl.find_all("dd")))
    for dt, dd in pairs:
        k = dt.get_text(" ", strip=True).rstrip(":").strip()
        v = dd.get_text(" ", strip=True)
        all_pairs.append((k, v))
        print(f"  '{k}'  →  '{v[:80]}'")
print(f"\n  Total pairs: {len(all_pairs)}")


# ─── 3. Auction-specific patterns ──────────────────────────────────────────
section("3) AUCTION-SPECIFIC DOM HINTS")

# Try to find data attributes / element IDs / classes
auction_classes = re.findall(r'class="([^"]*(?:auction|bid|countdown|timer|reserve|estimate)[^"]*)"', html, re.IGNORECASE)
print(f"\n  Auction-related CSS classes ({len(set(auction_classes))} unique):")
for c in sorted(set(auction_classes))[:30]:
    print(f"    {c}")

auction_ids = re.findall(r'id="([^"]*(?:auction|bid|countdown|timer|reserve|estimate)[^"]*)"', html, re.IGNORECASE)
print(f"\n  Auction-related IDs ({len(set(auction_ids))} unique):")
for i in sorted(set(auction_ids))[:20]:
    print(f"    {i}")


# ─── 4. Visible text hunt for auction fields (context grep) ─────────────────
section("4) FIELD CONTEXT EXTRACTION")
contexts = [
    ("estimate_range", r"(?:Sch.tzung|Estimation|Estimate)[\s\S]{1,400}"),
    ("bid_current", r"(?:Aktuelles Gebot|Offre actuelle|Current bid|Höchstgebot)[\s\S]{1,200}"),
    ("bid_count", r"(?:Anzahl Gebote|Offres|Bids|Gebote insgesamt)[\s\S]{1,150}"),
    ("watchers", r"(?:Beobachter|Observateurs|Watchers)[\s\S]{1,100}"),
    ("closes_at", r"(?:Endet|Se termine|Ends|Auktionsende)[\s\S]{1,150}"),
    ("reserve", r"(?:Mindestgebot|Prix de r.serve|Reserve|Mindestpreis)[\s\S]{1,150}"),
    ("status", r"(?:Auktionsverkauf|Status|Versteigerung läuft|Sold|Verkauft)[\s\S]{1,150}"),
]
for name, pat in contexts:
    matches = re.findall(pat, html)
    if matches:
        print(f"\n  === {name} === ({len(matches)} matches)")
        for m in matches[:2]:
            snip = re.sub(r"\s+", " ", m).strip()
            print(f"    {snip[:250]}")


# ─── 5. Embedded JSON data (Nuxt/Astro/etc state) ──────────────────────────
section("5) EMBEDDED FRAMEWORK STATE (Nuxt/Astro/etc)")
for var in ["__NUXT__", "__NEXT_DATA__", "__INITIAL_STATE__", "window.__data"]:
    if var in html:
        idx = html.find(var)
        print(f"\n  ✓ Found '{var}' at offset {idx}")
        # Try to extract a JSON-ish blob (very rough)
        chunk = html[idx:idx + 500]
        print(f"    sample: {chunk[:200]}")

# Astro hint
astro_hints = re.findall(r'data-astro-cid-\w+', html)
if astro_hints:
    print(f"\n  ✓ Astro framework detected ({len(set(astro_hints))} unique cids)")

# Mention of specific framework
if 'astro-island' in html:
    print("  ✓ astro-island components present (Astro SSR)")
if 'data-island' in html:
    print("  ✓ data-island attrs present")


# ─── 6. Look for any HTML chunk with prices/numbers near "Gebot" ────────────
section("6) BID-LIKE DOM CHUNKS (numeric near 'Gebot')")
bid_chunks = re.findall(r'>\s*(?:€\s*)?[\d.,]+\s*(?:€|EUR|kEUR|TEUR)?\s*<', html)
print(f"  Numeric chunks (€/EUR): {len(bid_chunks)}")
unique_amounts = sorted(set(b.strip("<> €EUR\n").replace(",", ".").replace(" ", "") for b in bid_chunks if b.strip("<> €EUR\n")), key=lambda x: -len(x))
for a in unique_amounts[:20]:
    print(f"    {a}")
