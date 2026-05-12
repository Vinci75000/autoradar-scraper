"""Quick recon script for classicdriver.com DOM structure.

Run from repo root:
    python -u scripts/cd_recon.py

Output: prints DOM patterns count + context, saves /tmp/cd_ferrari.html
"""
import re
import sys

import httpx

URL = "https://www.classicdriver.com/en/car/ferrari/296/2024/1026449"

r = httpx.get(
    URL,
    follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30.0,
)
text = r.text
print(f"HTTP status: {r.status_code}")
print(f"HTML length: {len(text)} bytes")

with open("/tmp/cd_ferrari.html", "w") as f:
    f.write(text)
print("Saved to /tmp/cd_ferrari.html")
print()

patterns = [
    ("h1 tag", r"<h1[^>]*>([^<]{5,200})</h1>"),
    ("dt count", r"<dt\b"),
    ("dd count", r"<dd\b"),
    ("field-name- count", r'class="[^"]*field-name-[^"]*"'),
    ("itemprop count", r'\bitemprop="'),
    ("Mileage context", r".{30}[Mm]ileage.{200}"),
    ("Year of manuf context", r".{30}Year of manufacture.{200}"),
    ("Price (USD/EUR) context", r".{20}(?:USD|EUR|GBP|CHF)\s*[\d\s\.]+.{50}"),
    ("Location context", r".{30}[Ll]ocation.{200}"),
    ("Country VAT", r".{30}Country VAT.{100}"),
    ("Drupal field-label", r'<[^>]+class="[^"]*field-label[^"]*"[^>]*>([^<]+)'),
]

for name, p in patterns:
    matches = re.findall(p, text, re.DOTALL)
    print(f"=== {name} ===")
    print(f"  count: {len(matches)}")
    for m in matches[:2]:
        snip = m if isinstance(m, str) else (m[0] if m else "")
        print(f"  {repr(snip)[:250]}")
    print()
