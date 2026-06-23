"""Validation qualite du generique durci — DRY, zero ecriture en base.

Rejoue les 10 dealers du run sur l'extracteur durci et montre, par fiche
gardee, mk | mo | yr | px. Les fiches droppees (SOLD, bruit, modele==dealer)
n'apparaissent pas : on lit l'effet a (count gardees) et a la proprete des
champs. But: confirmer annee reelle (pas 2026), modele sans suffixe site,
zero SOLD, et les 3 dealers morts (ac-classics, ac-autoclassic,
auto-salon-singen) qui tombent a ~0.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from dotenv import load_dotenv

load_dotenv(".env")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("extractors.extract_generic").setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING, format="%(message)s")

import scraper
from extractors.extract_generic import GenericJsonLdExtractor
from extractors.base import SourceConfig

SLUGS = [
    "classicgaragecelle", "classiccars-badenbaden", "classiccenter-koeln",
    "ac-autoclassic", "ac-classics", "sportwagen-adelmann", "arnold-classic",
    "auto-salon-singen", "crcars", "collection-car",
]

db = scraper.get_db()
rows = db.table("sources").select("*").in_("slug", SLUGS).execute().data
by_slug = {r["slug"]: r for r in rows}
ext = GenericJsonLdExtractor()

for slug in SLUGS:
    r = by_slug.get(slug)
    if not r:
        print("\n### %s — (introuvable dans sources)" % slug)
        continue
    cfg = SourceConfig(
        slug=slug,
        listings_url=r.get("listings_url"),
        country=(r.get("country") or "de"),
        currency=(r.get("currency") or "eur"),
        language=(r.get("language") or "en"),
        timezone=(r.get("timezone") or "Europe/Berlin"),
        tier=(r.get("tier") or 2),
        type=(r.get("type") or "dealer"),
        score_bonus=(r.get("score_bonus") or 3),
        scrape_method="generic_jsonld",
        selectors={},
    )
    try:
        res = ext.extract(cfg, limit=8)
    except Exception as exc:
        print("\n### %s — ERREUR extract: %s" % (slug, str(exc)[:120]))
        continue
    print("\n### %s — %d gardees / err=%d" % (slug, len(res.cars), len(res.errors)))
    for c in res.cars:
        print("   %-14s | %-44s | yr=%-6s | px=%s" % (
            (c.mk or "?"),
            (c.mo or "?")[:44],
            str(c.yr or "--"),
            str(int(c.px)) if c.px else "--",
        ))
