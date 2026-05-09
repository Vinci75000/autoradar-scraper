#!/usr/bin/env python3
"""
Etape 2 - Ingest dbpedia_models.json -> Supabase models_canonical.

Version urllib pure (zero dependency).
Utilise l API REST PostgREST de Supabase directement.

Idempotent: UPSERT par (mk, mo). Re-run safe.

Prerequis:
  1. Migration 2026_05_09_models_canonical.sql appliquee
  2. Variables env: SUPABASE_URL + SUPABASE_SERVICE_KEY

Usage:
  cd ~/Code/autoradar/scraper
  set -a; source .env; set +a
  python -u tools/dbpedia_ingest_to_supabase.py
"""
import json
import os
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone

JSON_PATH = "data/dbpedia_models.json"
TABLE = "models_canonical"
BATCH_SIZE = 200
TIMEOUT = 60


def http_request(method, url, headers, data=None):
    """Retourne (status_code, body_str, headers_dict)."""
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, payload, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        h = dict(e.headers) if e.headers else {}
        return e.code, body, h


def main():
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

    if not url or not key:
        print("ERROR: SUPABASE_URL et SUPABASE_SERVICE_KEY requis dans l env", file=sys.stderr)
        print("       Run: set -a; source .env; set +a", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(JSON_PATH):
        print(f"ERROR: {JSON_PATH} introuvable. Run d abord dbpedia_ingest_models.py", file=sys.stderr)
        sys.exit(1)

    print(f"== Ingest DBpedia -> {TABLE} (urllib + PostgREST) ==\n")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    models = data.get("models", [])
    print(f"Loaded {len(models)} models from {JSON_PATH}")
    print(f"Source generated: {data.get('generated_at', 'unknown')}")
    print(f"Brands queried:   {data.get('brands_queried', '?')}")
    print(f"Brands failed:    {data.get('brands_failed', [])}\n")

    if not models:
        return 0

    rest_url = url.rstrip("/") + f"/rest/v1/{TABLE}"

    headers_upsert = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    headers_get = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    n_batches = (len(models) + BATCH_SIZE - 1) // BATCH_SIZE
    total_ok = 0
    total_err = 0
    failed_batches = []

    for i in range(0, len(models), BATCH_SIZE):
        batch = models[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        rows = []
        for m in batch:
            if not m.get("mk") or not m.get("mo"):
                continue
            row = {
                "mk": m["mk"],
                "mo": m["mo"],
                "label_full": m.get("label_full"),
                "yr_start": m.get("yr_start"),
                "yr_end": m.get("yr_end"),
                "body_styles": m.get("body_styles") or None,
                "dbpedia_uri": m.get("dbpedia_uri"),
                "wikidata_qid": m.get("wikidata_qid") or None,
                "source": "dbpedia",
                "last_synced_at": now_iso,
            }
            rows.append(row)

        if not rows:
            continue

        upsert_url = rest_url + "?on_conflict=mk,mo"
        status, body, _ = http_request("POST", upsert_url, headers_upsert, rows)

        if 200 <= status < 300:
            total_ok += len(rows)
            print(f"  Batch {batch_num}/{n_batches}: OK ({len(rows)} rows)", flush=True)
        else:
            total_err += 1
            failed_batches.append(batch_num)
            print(f"  Batch {batch_num}/{n_batches}: FAIL HTTP {status} - {body[:300]}", flush=True)

    print(f"\n== Resultat ingest ==")
    print(f"  Rows OK:      {total_ok}")
    print(f"  Batchs FAIL:  {total_err}")
    if failed_batches:
        print(f"  Batchs en echec: {failed_batches}")

    # Verification post-ingest
    print(f"\n== Verification {TABLE} ==")

    # Count total via Prefer: count=exact + Range
    count_headers = dict(headers_get)
    count_headers["Prefer"] = "count=exact"
    count_headers["Range-Unit"] = "items"
    count_headers["Range"] = "0-0"

    status, body, resp_headers = http_request(
        "GET",
        rest_url + "?select=id",
        count_headers,
    )

    total_db = None
    if 200 <= status < 300:
        cr = resp_headers.get("Content-Range") or resp_headers.get("content-range", "")
        if "/" in cr:
            try:
                total_db = int(cr.split("/")[-1])
            except ValueError:
                pass
    if total_db is not None:
        print(f"  Total dans table: {total_db}")
    else:
        print(f"  Count via header indispo (HTTP {status})")

    # Top 10 marques (fetch all mk)
    status, body, _ = http_request(
        "GET",
        rest_url + "?select=mk&limit=10000",
        headers_get,
    )
    if 200 <= status < 300:
        rows_db = json.loads(body)
        counter = Counter(r["mk"] for r in rows_db)
        print(f"\n  Top 10 marques en DB:")
        for mk, count in counter.most_common(10):
            print(f"    {mk:25s} {count}")
    else:
        print(f"  Top marques FAIL: HTTP {status} - {body[:200]}")

    # Echantillon 5 modeles avec dates + Q-ID
    sample_url = (
        rest_url
        + "?select=mk,mo,yr_start,yr_end,body_styles,wikidata_qid"
        + "&yr_start=not.is.null"
        + "&wikidata_qid=not.is.null"
        + "&limit=5"
    )
    status, body, _ = http_request("GET", sample_url, headers_get)
    if 200 <= status < 300:
        sample = json.loads(body)
        print(f"\n  Echantillon 5 modeles (dates + Q-ID):")
        for r in sample:
            bs_list = r.get("body_styles") or []
            bs = ",".join(bs_list)[:30]
            period = f"{r.get('yr_start') or '?'}-{r.get('yr_end') or '?'}"
            qid = r.get("wikidata_qid") or "-"
            print(f"    {r['mk']:15s} {r['mo']:30s} {period:14s} {qid:12s} body={bs}")
    else:
        print(f"  Sample FAIL: HTTP {status}")

    print(f"\nDone.")
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
