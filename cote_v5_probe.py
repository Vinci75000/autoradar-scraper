"""cote_v5_probe.py — CARNET / AutoRadar
==========================================
Teste si refresh_cote_segments_v5() (matching 2-pass) est DEPLOYE en base, et
montre ce qu'elle produit (segments, pass1/pass2). C'est le refresh de prod
(idempotent : reconstruit cote_segments depuis cars active). NE TOUCHE PAS au
cron — sert a decider si on bascule le cron vers v5.

Apres l'avoir lance : verifie que la cote LIVE dans l'app repond toujours bien
(le Worker lit cote_segments par mo_canon). Si oui -> on bascule le cron en v5.

  python3 cote_v5_probe.py
"""
import os, sys, json, time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

_p = Path(__file__).resolve()
for _cand in (_p.parent, _p.parent.parent):
    if (_cand / ".env").exists():
        load_dotenv(_cand / ".env")
        break


def call(sb, fn):
    try:
        r = sb.rpc(fn, {}).execute()
        return r.data or {}, None
    except Exception as e:
        return None, str(e)


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("[cote_v5] manque SUPABASE_URL ou SUPABASE_SERVICE_KEY", file=sys.stderr)
        return 1
    sb = create_client(url, key)

    print("appel RPC refresh_cote_segments_v5() ...")
    t0 = time.time()
    d, err = call(sb, "refresh_cote_segments_v5")
    if err:
        print("\nv5 INDISPONIBLE : %s" % err)
        print(">>> la migration v5 n'est pas deployee. Applique migrations/refresh_cote_segments_v5.sql")
        print("    dans le SQL editor Supabase, puis relance ce probe.")
        return 1
    ms = int((time.time() - t0) * 1000)
    print(json.dumps(d, ensure_ascii=False, indent=2))
    print("\nv5 OK (%d ms reseau inclus)" % ms)
    print("  segments_count = %s" % d.get("segments_count"))
    print("  cars_processed = %s" % d.get("cars_processed"))
    print("  pass1_updated  = %s  (match exact)" % d.get("pass1_updated"))
    print("  pass2_updated  = %s  (first_token : C 200 -> C-Class)" % d.get("pass2_updated"))
    print("\n>>> Verifie maintenant la cote LIVE dans l'app. Si elle repond bien,")
    print("    on bascule le cron (scripts/refresh_cote_segments.py) de l'ancienne vers v5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
