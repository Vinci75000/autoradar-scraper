#!/usr/bin/env python3
"""
scripts/onboard_source.py

Onboarding semi-auto d'une nouvelle source de cars.

Workflow en 4 phases :
    1. SNIFF       — sniff.sniff_url() détecte la plateforme
    2. SMOKE TEST  — vérifie >= MIN_DETAIL_URLS URLs de fiches détectées
    3. REGISTER    — upsert dans `sources` (DB) + dealers.yaml
    4. REPORT      — print summary humain (ou JSON pour batch)

Le smoke test est volontairement léger : on s'appuie sur le circuit breaker
livré dans cron_runs.py pour attraper les sources qui échouent au runtime.

Usage:
    python -m scripts.onboard_source URL
    python -m scripts.onboard_source URL --name myDealer --tier collector
    python -m scripts.onboard_source URL --dry-run                # ne touche pas la DB
    python -m scripts.onboard_source URL --yaml config/dealers.yaml
    python -m scripts.onboard_source URL --json                   # pour batch processing

Exit codes:
    0 = source ready (scrapable)
    1 = manual_inspect requis
    2 = erreur fatale (URL inaccessible, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# ── Constantes ───────────────────────────────────────────

MIN_DETAIL_URLS = 5        # minimum d'URLs détail pour considérer source ready
DEFAULT_TIER = 'mainstream'
TIER_OPTIONS = ('collector', 'mainstream')

# Mapping platform → nom canonique d'extractor (utilisé par les crons existants)
PLATFORM_TO_EXTRACTOR = {
    'symfio_v1':     'symfio_v1',
    'symfio_v2':     'symfio_v2',
    'rivamedia':     'rivamedia',
    'drupal':        'drupal_generic',
    'inertia':       'inertia_generic',
    'generic_cards': 'generic_cards',
}

# Mapping platform → cron qui prendra cette source en charge
PLATFORM_TO_CRON = {
    'symfio_v1':     'symfio_cron',
    'symfio_v2':     'symfio_cron',
    'rivamedia':     'dealers_cron',
    'drupal':        'dealers_cron',
    'inertia':       'phase_a_cron',
    'generic_cards': 'dealers_cron',
}


# ── Résultat d'un onboarding ─────────────────────────────

@dataclass
class OnboardResult:
    """Résultat complet d'un onboarding pour reporting et batch."""
    url: str
    name: str
    platform: str
    confidence: float
    tier: str
    status: str  # 'ready', 'manual_inspect', 'error'
    sniff_hints: list[str] = field(default_factory=list)
    urls_detected_count: int = 0
    smoke_passed: bool = False
    smoke_reason: str = ''
    registered_in_db: bool = False
    registered_in_yaml: bool = False
    suggested_cron: Optional[str] = None
    suggested_extractor: Optional[str] = None
    next_steps: list[str] = field(default_factory=list)
    error: Optional[str] = None
    needs_playwright: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def exit_code(self) -> int:
        if self.status == 'ready':
            return 0
        if self.status == 'manual_inspect':
            return 1
        return 2


# ── Helpers ──────────────────────────────────────────────

def _normalize_source_name(url: str, explicit_name: Optional[str] = None) -> str:
    """
    Génère un identifiant slug-friendly pour la source.

    >>> _normalize_source_name('https://www.mechatronik.de/fahrzeuge.html')
    'mechatronik_de'
    >>> _normalize_source_name('https://example.com', explicit_name='My Cool Dealer!')
    'my_cool_dealer_'
    """
    if explicit_name:
        return re.sub(r'[^a-z0-9_]', '_', explicit_name.lower()).strip('_')[:50] or 'unnamed'
    host = urlparse(url).netloc
    host = host.replace('www.', '').replace('.', '_').replace('-', '_')
    return re.sub(r'[^a-z0-9_]', '_', host.lower()).strip('_')[:50] or 'unnamed'


def _smoke_test(sniff_result) -> tuple[bool, str]:
    """
    Smoke test léger : a-t-on assez de signal pour considérer la source ready ?

    Le vrai test sera fait par le cron au premier run, avec le circuit breaker
    en backup si ça plante 3x.

    Returns:
        (passed: bool, reason: str)
    """
    if getattr(sniff_result, 'error', None):
        return False, f'sniff error: {sniff_result.error}'
    if getattr(sniff_result, 'needs_playwright', False):
        return False, 'needs_playwright — Cloudflare ou JS-heavy'
    if sniff_result.platform in ('unknown', 'error'):
        return False, f'platform={sniff_result.platform}'
    if sniff_result.confidence < 0.5:
        return False, f'confidence trop basse ({sniff_result.confidence:.2f} < 0.5)'
    urls_count = len(getattr(sniff_result, 'urls_detected', []))
    if urls_count < MIN_DETAIL_URLS:
        return False, f'seulement {urls_count} URLs détail (besoin >= {MIN_DETAIL_URLS})'
    return True, f'{urls_count} URLs détail · platform={sniff_result.platform} · conf={sniff_result.confidence:.2f}'


def _register_in_db(result: OnboardResult) -> bool:
    """
    Upsert dans la table `sources` (Supabase).

    Table attendue (à créer si pas existante) :
        sources (
            name TEXT PRIMARY KEY,
            base_url TEXT,
            platform TEXT,
            extractor TEXT,
            tier TEXT,
            status TEXT,
            enabled BOOLEAN,
            sniff_confidence FLOAT,
            sniff_hints JSONB,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ
        )

    Si la table n'existe pas ou si SUPABASE_URL n'est pas configuré → False.
    """
    try:
        from supabase import create_client
    except ImportError:
        print('[onboard] supabase client not installed, skipping DB register', file=sys.stderr)
        return False
    try:
        sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            'name': result.name,
            'base_url': result.url,
            'platform': result.platform,
            'extractor': PLATFORM_TO_EXTRACTOR.get(result.platform, 'manual'),
            'tier': result.tier,
            'status': result.status,
            'enabled': result.status == 'ready',
            'sniff_confidence': result.confidence,
            'sniff_hints': result.sniff_hints,
            'updated_at': now_iso,
        }
        # Upsert : si la source existe déjà, on update updated_at + status
        # Si elle n'existe pas, on l'insère avec created_at
        existing = sb.table('sources').select('name').eq('name', result.name).execute()
        if not existing.data:
            payload['created_at'] = now_iso
        sb.table('sources').upsert(payload, on_conflict='name').execute()
        return True
    except KeyError as e:
        print(f'[onboard] missing env var: {e}', file=sys.stderr)
        return False
    except Exception as e:
        print(f'[onboard] register_in_db failed: {type(e).__name__}: {e}', file=sys.stderr)
        return False


def _update_yaml(result: OnboardResult, yaml_path: Path) -> bool:
    """
    Append la source dans dealers.yaml (idempotent — skip si déjà présent).

    Format ajouté :
        - name: dealer_xx
          base_url: https://...
          platform: symfio_v1
          extractor: symfio_v1
          tier: mainstream
          status: ready
          enabled: true
    """
    try:
        existing = yaml_path.read_text(encoding='utf-8') if yaml_path.exists() else 'sources:\n'
        if f'name: {result.name}\n' in existing or f'name: {result.name}\r\n' in existing:
            return True  # déjà présent, no-op idempotent
        # Si le fichier n'a pas de clef 'sources:', on l'ajoute en tête
        if 'sources:' not in existing:
            existing = 'sources:\n' + existing
        entry = (
            f"  - name: {result.name}\n"
            f"    base_url: {result.url}\n"
            f"    platform: {result.platform}\n"
            f"    extractor: {PLATFORM_TO_EXTRACTOR.get(result.platform, 'manual')}\n"
            f"    tier: {result.tier}\n"
            f"    status: {result.status}\n"
            f"    enabled: {'true' if result.status == 'ready' else 'false'}\n"
            f"    sniff_confidence: {result.confidence:.2f}\n"
        )
        # Append (avec un newline propre)
        if not existing.endswith('\n'):
            existing += '\n'
        yaml_path.write_text(existing + entry, encoding='utf-8')
        return True
    except Exception as e:
        print(f'[onboard] update_yaml failed: {type(e).__name__}: {e}', file=sys.stderr)
        return False


# ── Pipeline principal ────────────────────────────────────

def onboard(
    url: str,
    explicit_name: Optional[str] = None,
    tier: str = DEFAULT_TIER,
    dry_run: bool = False,
    yaml_path: Optional[Path] = None,
    sniff_fn=None,  # injectable pour tests
) -> OnboardResult:
    """
    Orchestre les 4 phases de l'onboarding et retourne un OnboardResult.

    Args:
        url: URL de la page listing du marchand
        explicit_name: nom personnalisé (défaut: dérivé du domaine)
        tier: 'collector' ou 'mainstream'
        dry_run: si True, ne touche pas la DB ni le YAML
        yaml_path: chemin vers dealers.yaml (optionnel)
        sniff_fn: fonction de sniff à utiliser (défaut: autoradar.extractors.sniff.sniff_url)
                  utile pour les tests (injection d'un mock)
    """
    # 1. SNIFF (lazy import pour permettre injection en test)
    if sniff_fn is None:
        from extractors.sniff import sniff_url as sniff_fn  # type: ignore

    name = _normalize_source_name(url, explicit_name)
    print(f'[onboard] sniff {url} ...', file=sys.stderr)
    sniff = sniff_fn(url)

    # 2. SMOKE TEST
    smoke_ok, smoke_reason = _smoke_test(sniff)

    # 3. DECIDE STATUS
    if getattr(sniff, 'error', None):
        status = 'error'
    elif smoke_ok:
        status = 'ready'
    else:
        status = 'manual_inspect'

    # 4. CONSTRUCT RESULT
    result = OnboardResult(
        url=url, name=name,
        platform=sniff.platform,
        confidence=sniff.confidence,
        tier=tier, status=status,
        sniff_hints=list(getattr(sniff, 'hints', [])),
        urls_detected_count=len(getattr(sniff, 'urls_detected', [])),
        smoke_passed=smoke_ok,
        smoke_reason=smoke_reason,
        error=getattr(sniff, 'error', None),
        needs_playwright=getattr(sniff, 'needs_playwright', False),
    )
    result.suggested_cron = PLATFORM_TO_CRON.get(sniff.platform)
    result.suggested_extractor = PLATFORM_TO_EXTRACTOR.get(sniff.platform)

    # 5. REGISTER (skip si dry-run ou status=error)
    if not dry_run and status in ('ready', 'manual_inspect'):
        result.registered_in_db = _register_in_db(result)
        if yaml_path:
            result.registered_in_yaml = _update_yaml(result, yaml_path)

    # 6. NEXT STEPS narratifs
    if status == 'ready':
        result.next_steps = [
            f'Source enregistrée en status=ready, enabled=true',
            f'Au prochain run de {result.suggested_cron}, elle sera scrapée automatiquement',
            f'Surveille /admin/ops pour vérifier le premier run et le circuit breaker',
        ]
    elif status == 'manual_inspect':
        steps = [f'Source enregistrée en status=manual_inspect · raison : {smoke_reason}']
        if result.needs_playwright:
            steps.append('Cloudflare/JS détecté · ajouter un extractor Playwright dédié')
        elif sniff.platform in ('unknown', 'error'):
            steps.append('Inspecter le HTML manuellement pour identifier la plateforme')
        else:
            steps.append('Ajuster les selectors CSS dans le module extractor correspondant')
        steps.append('Une fois corrigée, relancer : onboard_source URL --name X')
        result.next_steps = steps
    else:
        result.next_steps = [
            f'Erreur : {result.error or "URL inaccessible"}',
            'Vérifier l\'URL et la connectivité',
        ]

    return result


# ── Reporting ────────────────────────────────────────────

def _print_report(r: OnboardResult, dry_run: bool):
    """Pretty-print human-readable report — sober, mantra smart/light/clean."""
    print()
    print(f'  ── {r.name} ──')
    print(f'  URL          {r.url}')
    print(f'  Platform     {r.platform}  ·  confidence {r.confidence:.2f}')
    print(f'  Tier         {r.tier}')
    if r.sniff_hints:
        print(f'  Indices')
        for h in r.sniff_hints[:5]:
            print(f'    · {h}')
    print(f'  URLs detail  {r.urls_detected_count}')
    smoke_glyph = '✓' if r.smoke_passed else '✗'
    print(f'  Smoke test   {smoke_glyph}  {r.smoke_reason}')
    print(f'  Status       {r.status}')
    if not dry_run:
        if r.registered_in_db:
            print(f'  DB           ✓ registered (table sources)')
        else:
            print(f'  DB           — not registered')
        if r.registered_in_yaml:
            print(f'  YAML         ✓ appended')
    else:
        print(f'  Mode         dry-run · aucune écriture')
    if r.suggested_cron:
        print(f'  Cron suggéré {r.suggested_cron}  ·  extractor {r.suggested_extractor}')
    print()
    print('  Prochaines étapes')
    for step in r.next_steps:
        print(f'    · {step}')
    print()


# ── CLI ──────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(
        description='Onboarding semi-auto d\'une nouvelle source de cars',
        epilog='Exit codes : 0=ready, 1=manual_inspect, 2=error'
    )
    p.add_argument('url', help='URL de la page listing du marchand')
    p.add_argument('--name', help='Nom personnalisé (défaut : dérivé du domaine)')
    p.add_argument('--tier', choices=TIER_OPTIONS, default=DEFAULT_TIER,
                   help=f'collector | mainstream (défaut : {DEFAULT_TIER})')
    p.add_argument('--dry-run', action='store_true',
                   help='Sniff et smoke test seulement, sans écriture DB ni YAML')
    p.add_argument('--yaml', type=Path, default=None,
                   help='Chemin vers dealers.yaml à mettre à jour')
    p.add_argument('--json', action='store_true',
                   help='Output JSON (utile pour batch)')
    args = p.parse_args(argv)

    result = onboard(
        url=args.url,
        explicit_name=args.name,
        tier=args.tier,
        dry_run=args.dry_run,
        yaml_path=args.yaml,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print_report(result, dry_run=args.dry_run)

    sys.exit(result.exit_code)


if __name__ == '__main__':
    main()
