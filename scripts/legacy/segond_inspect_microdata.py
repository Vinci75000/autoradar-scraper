#!/usr/bin/env python3
"""
Segond — Étape 0.5 : inspect microdata.

Objectif : dumper TOUS les nœuds itemscope/itemtype Schema.org sur 2 fiches
diverses (Lambo Huracan Sterrato, Audi A1) pour cataloguer exactement quels
itemprops Vehicle sont disponibles. Sans présupposé sur lequel est "le bon".

Output structuré par nœud :
  - itemtype complet
  - selector CSS suggéré (tag + class + id)
  - liste des itemprops avec valeurs (200 chars max)

À partir de ça on construit le vrai extracteur étape 1.

Usage :
    cd ~/Code/autoradar/scraper
    python -u segond_inspect_microdata.py
"""
from __future__ import annotations

import re
import sys
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag

URLS = [
    "https://www.segond-automobiles.com/vehicules/lamborghini/2003751-lamborghini-huracan-sterrato-5-2-v10-610-4wd-ldf7/",
    "https://www.segond-automobiles.com/vehicules/audi/2000136-audi-a1-sportback-a1-sportback-30-tfsi-116-ch-s-tronic-7/",
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def fetch(url: str, timeout: int = 20) -> Optional[str]:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            print(f"  [{r.status_code}] {url}")
        except requests.RequestException as e:
            print(f"  [err {attempt+1}/3] {e}")
        time.sleep(1.5)
    return None


def node_selector(node: Tag) -> str:
    """Genère un selector CSS lisible pour identifier le nœud."""
    tag = node.name
    el_id = node.get("id")
    cls = node.get("class") or []
    parts = [tag]
    if el_id:
        parts.append(f"#{el_id}")
    if cls:
        # garde max 3 classes pour rester lisible
        parts.append("." + ".".join(cls[:3]))
    return "".join(parts)


def is_direct_itemscope_child(parent: Tag, child: Tag) -> bool:
    """
    True si child est un itemprop direct de parent (pas dans un itemscope nested).
    Permet de séparer les itemprops d'un Vehicle vs ceux d'un Offer imbriqué.
    """
    cur = child.parent
    while cur and cur is not parent:
        if cur.has_attr("itemscope"):
            return False
        cur = cur.parent
    return True


def dump_itemscope(node: Tag, depth: int = 0) -> None:
    """Dump récursif d'un nœud itemscope avec ses itemprops directs et nested."""
    indent = "  " * depth
    itemtype = node.get("itemtype", "(no itemtype)")
    sel = node_selector(node)

    print(f"{indent}┌─ NODE [{itemtype}]")
    print(f"{indent}│  selector: {sel}")

    # itemprops directs (pas dans un nested itemscope)
    direct_props: list[tuple[str, str]] = []
    for el in node.find_all(attrs={"itemprop": True}):
        if not is_direct_itemscope_child(node, el):
            continue
        key = el.get("itemprop")
        # ne pas inclure les itemprops qui ouvrent un nouveau itemscope (gérés en récursion)
        if el.has_attr("itemscope"):
            continue
        val = el.get("content") or el.get("value") or el.get_text(" ", strip=True)
        if val:
            direct_props.append((key, val[:200]))

    if direct_props:
        print(f"{indent}│  itemprops directs ({len(direct_props)}):")
        for k, v in direct_props:
            v_short = (v[:100] + "…") if len(v) > 100 else v
            print(f"{indent}│    {k:30s} = {v_short}")
    else:
        print(f"{indent}│  (aucun itemprop direct)")

    # nested itemscopes
    nested = [
        n for n in node.find_all(attrs={"itemscope": True})
        if n is not node and is_direct_itemscope_child(node, n)
    ]
    if nested:
        print(f"{indent}│  nested itemscopes ({len(nested)}):")
        for n in nested:
            dump_itemscope(n, depth + 1)
    print(f"{indent}└─")


def main() -> int:
    print("=" * 70)
    print("Segond — Étape 0.5 : inspect microdata")
    print("=" * 70)

    for url in URLS:
        print(f"\n{'#' * 70}")
        print(f"# URL : {url}")
        print(f"{'#' * 70}")
        html = fetch(url)
        if not html:
            print("❌ fetch échoué")
            continue

        soup = BeautifulSoup(html, "html.parser")

        # tous les nœuds itemscope+itemtype racines (pas dans un autre itemscope)
        all_scopes = soup.find_all(attrs={"itemscope": True, "itemtype": True})
        # filtre racines : pas inclus dans un autre itemscope
        roots = []
        for n in all_scopes:
            parent = n.parent
            is_root = True
            while parent:
                if isinstance(parent, Tag) and parent.has_attr("itemscope"):
                    is_root = False
                    break
                parent = parent.parent
            if is_root:
                roots.append(n)

        print(f"\n  Total itemscope+itemtype nœuds : {len(all_scopes)}")
        print(f"  Dont racines (top-level)        : {len(roots)}")

        # liste tous les itemtypes uniques rencontrés
        all_itemtypes = sorted(set(n.get("itemtype") for n in all_scopes))
        print(f"\n  Itemtypes uniques sur la page :")
        for it in all_itemtypes:
            count = sum(1 for n in all_scopes if n.get("itemtype") == it)
            print(f"    [{count}x] {it}")

        # dump détaillé des racines
        print(f"\n  --- DUMP RACINES ---")
        for i, root in enumerate(roots, 1):
            print(f"\n  ROOT #{i}/{len(roots)}")
            dump_itemscope(root)

        time.sleep(1.0)

    print("\n" + "=" * 70)
    print("Inspection terminée. À partir de ce dump on identifie :")
    print("  1. Le selector exact pour le nœud Schema.org Vehicle")
    print("  2. Les itemprops disponibles (price, mileage, year, gear, etc.)")
    print("  3. Si Offer est nested ou frère du Vehicle")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
