import os, sys, re, json, time, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

cfg = {}
E = Path(".env")
if E.exists():
    for line in E.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), "").rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper()), None)

def get(params, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:-")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180))
        except Exception as e:
            if i == tries - 1: raise
            print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 5 * i)

print("=== A · quelles sources posent une fausse punaise / ci=pays ===")
for lab, q in (
    ("lat=51.1638175", {"lat": "eq.51.1638175"}),
    ("lat=54.5 lng=-2.5", {"lat": "eq.54.5", "lng": "eq.-2.5"}),
    ("ci=Allemagne", {"ci": "eq.Allemagne"}),
):
    c = Counter()
    for off in (0, 1000, 2000, 3000, 4000, 5000):
        p = dict(q, select="src", status="eq.active", limit="1000", offset=str(off))
        try:
            rows = get(p)
        except Exception as e:
            print("    offset %d ERR %r" % (off, e)); break
        if not rows: break
        for r in rows: c[r.get("src") or "(null)"] += 1
        if len(rows) < 1000: break
    print("  %-20s total=%d" % (lab, sum(c.values())))
    for s, n in c.most_common(10):
        print("      %6d  %s" % (n, s))

print("")
print("=== B · verdict endsAt sur les 32 encheres C&C 'actives' ===")
rows = get({"select": "id,src_url,mk,mo,yr,px", "src": "ilike.*andclassic*",
            "status": "eq.active", "src_url": "ilike.*/auctions/*", "limit": "60"})
print("  a sonder : %d" % len(rows))

RX_END = re.compile(r'"endsAt"\s*:\s*"([^"]+)"')
RX_BID = re.compile(r'"bid_amount"\s*:\s*(\d+)')
RX_CNT = re.compile(r'"bid_count"\s*:\s*(\d+)')
RX_DSP = re.compile(r'"bid_amount_display"\s*:\s*"([^"]{1,20})')
RX_RES = re.compile(r'"isReserveMet"\s*:\s*(true|false)')

now = datetime.now(timezone.utc)
from playwright.sync_api import sync_playwright
out, stats = [], Counter()
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    for i, r0 in enumerate(rows, 1):
        if i > 1 and i % 20 == 1:
            print("  ... pause 45s"); time.sleep(45)
        try:
            pg.goto(r0["src_url"], wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(2500)
            h = pg.content()
            m = RX_END.search(h)
            if not m:
                stats["SANS_ENDSAT"] += 1
                print("  %3d SANS_ENDSAT  %s %s" % (i, r0.get("mk"), r0.get("mo")))
                continue
            end = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
            ho = (end - now).total_seconds() / 3600.0
            v = "CLOSE" if ho <= 0 else ("LIVE" if ho <= 72 else "UPCOMING")
            bid = RX_BID.search(h); cnt = RX_CNT.search(h)
            dsp = RX_DSP.search(h); res = RX_RES.search(h)
            cur = "GBP" if (dsp and "\u00a3" in dsp.group(1)) else ("EUR" if dsp else "?")
            stats[v] += 1; stats["cur:" + cur] += 1
            print("  %3d %-8s h_offset=%9.1f  px_db=%-8s bid=%-8s %s bids=%-4s res=%-5s %s %s" % (
                i, v, ho, r0.get("px"), bid.group(1) if bid else "-", cur,
                cnt.group(1) if cnt else "-", res.group(1) if res else "-",
                r0.get("mk"), r0.get("mo")))
            out.append([r0["id"], v, "%.2f" % ho, m.group(1),
                        bid.group(1) if bid else "", cur, cnt.group(1) if cnt else "",
                        res.group(1) if res else "", r0["src_url"]])
        except Exception as e:
            stats["ERR"] += 1
            print("  %3d ERR %r" % (i, e))
        time.sleep(3.5)
    pg.close()

with open("/tmp/cc_endsat.tsv", "w") as f:
    for r in out:
        f.write("\t".join(str(x) for x in r) + "\n")
print("")
print("  bilan : %s" % dict(stats))
print("  -> /tmp/cc_endsat.tsv (%d lignes)" % len(out))
