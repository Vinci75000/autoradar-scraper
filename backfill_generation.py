"""backfill_generation.py — CARNET / AutoRadar
Remplit cars.generation + cars.gen_family sur tout le corpus, depuis cote_gen.py
(SOURCE UNIQUE des faits generation). Additif, idempotent, re-runnable.

Prerequis : avoir passe add_cars_generation.sql (colonnes + index).
  python3 -u backfill_generation.py --dry     # compte + distribution, n'ecrit rien
  python3 -u backfill_generation.py --write    # ecrit par batch (id IN), avec retries

Ecriture par groupe (code, famille) -> un UPDATE id IN [...] par chunk : quelques
centaines d'appels au lieu de 34k. Re-lancer ecrase avec les memes valeurs (safe).
"""
import sys
import time
from scraper import get_db
from cote_gen import infer_generation

db = get_db()
CHUNK = 150


def fetch_all():
    rows, off = [], 0
    while True:
        b = db.table("cars").select("id,mk,mo,yr").order("id").range(off, off + 998).execute().data
        if not b:
            break
        rows.extend(b)
        if len(b) < 999:
            break
        off += 999
    return rows


def main():
    write = "--write" in sys.argv

    # garde-fou : colonnes presentes ?
    try:
        db.table("cars").select("generation,gen_family").limit(1).execute()
    except Exception as e:
        print("Colonnes absentes -> passe d'abord add_cars_generation.sql dans Supabase.")
        print("  detail:", str(e)[:140])
        return 1

    cars = fetch_all()
    print("cars total : %d" % len(cars))

    groups = {}
    n_match = 0
    for c in cars:
        fam, code = infer_generation(c.get("mk"), c.get("mo"), c.get("yr"))
        if code:
            n_match += 1
            groups.setdefault((code, fam), []).append(c["id"])

    pct = 100.0 * n_match / max(len(cars), 1)
    print("avec generation : %d (%.1f%%)  |  %d groupes (code, famille)" % (n_match, pct, len(groups)))
    print("\ntop 18 groupes :")
    for (code, fam), ids in sorted(groups.items(), key=lambda x: -len(x[1]))[:18]:
        print("   %-10s %-18s %d" % (code, str(fam)[:18], len(ids)))

    if not write:
        print("\n(dry-run) — relance avec --write pour ecrire.")
        return 0

    print("\n--- ecriture ---")
    done = 0
    for (code, fam), ids in groups.items():
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            ok = False
            for attempt in range(5):
                try:
                    db.table("cars").update({"generation": code, "gen_family": fam}).in_("id", chunk).execute()
                    ok = True
                    break
                except Exception as e:
                    if attempt == 4:
                        print("  FAIL %-10s %s" % (code, str(e)[:90]))
                    time.sleep(1.5 * (attempt + 1))
            if ok:
                done += len(chunk)
    print("\ntotal ecrits : %d / %d attendus" % (done, n_match))

    # verif post-ecriture : combien de lignes ont generation non-null
    try:
        chk, off, cnt = [], 0, 0
        while True:
            b = db.table("cars").select("id").not_.is_("generation", "null").order("id").range(off, off + 998).execute().data
            if not b:
                break
            cnt += len(b)
            if len(b) < 999:
                break
            off += 999
        print("verif : %d lignes avec generation non-null en base" % cnt)
    except Exception as e:
        print("verif skip:", str(e)[:90])
    return 0


if __name__ == "__main__":
    sys.exit(main())
