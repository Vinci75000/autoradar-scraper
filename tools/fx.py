import json, urllib.request
from datetime import datetime, timedelta

UA = {"User-Agent": "CARNET-registre/1.0 (contact: schaillout@gmail.com)"}
_CACHE = {}

def _frankfurter(day, cur):
    u = "https://api.frankfurter.dev/v1/%s?base=%s&symbols=EUR" % (day, cur)
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
    return float(r["rates"]["EUR"]), "frankfurter.dev(%s)" % r.get("date", day)

def _ecb(day, cur):
    """BCE SDMX : serie D.<CUR>.EUR.SP00.A = <CUR> pour 1 EUR. On inverse."""
    d = datetime.strptime(day, "%Y-%m-%d")
    start = (d - timedelta(days=12)).strftime("%Y-%m-%d")
    u = ("https://data-api.ecb.europa.eu/service/data/EXR/D.%s.EUR.SP00.A"
         "?startPeriod=%s&endPeriod=%s&format=csvdata" % (cur, start, day))
    txt = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode("utf-8", "replace")
    lines = [l for l in txt.strip().split("\n") if l.strip()]
    head = [h.strip().strip('"') for h in lines[0].split(",")]
    it, iv = head.index("TIME_PERIOD"), head.index("OBS_VALUE")
    last = None
    for l in lines[1:]:
        c = [x.strip().strip('"') for x in l.split(",")]
        if len(c) > max(it, iv) and c[iv]:
            last = (c[it], float(c[iv]))
    if not last:
        raise RuntimeError("BCE : aucune observation")
    return 1.0 / last[1], "ecb(%s)" % last[0]

def rate(day, cur):
    if cur == "EUR":
        return 1.0, "identite"
    k = (day, cur)
    if k in _CACHE:
        return _CACHE[k]
    errs = []
    for fn in (_frankfurter, _ecb):
        try:
            v, srcname = fn(day, cur)
            _CACHE[k] = (v, srcname)
            return v, srcname
        except Exception as e:
            errs.append("%s:%r" % (fn.__name__, e))
    _CACHE[k] = (None, " | ".join(errs))
    return None, " | ".join(errs)

if __name__ == "__main__":
    for d in ("2026-05-28", "2026-06-22", "2026-06-19"):
        v, s = rate(d, "GBP")
        print("  %s GBP->EUR = %s   via %s" % (d, ("%.5f" % v) if v else "INDISPONIBLE", s))
