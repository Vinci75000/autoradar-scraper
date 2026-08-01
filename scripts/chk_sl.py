import sys; sys.path.insert(0, ".")
exec(open("bf_ml.py").read().split("print(\"lignes avec")[0])
rows = get({"select": "id,mk,mo,de,feat_serie_limitee", "status": "eq.active", "de": "not.is.null", "order": "id.asc", "limit": "500"})
import re
from extractors.keywords_multilang import KEYWORDS_BY_LANG
pats = []
for lg, ax in KEYWORDS_BY_LANG.items():
    for p in (ax.get("origine") or {}).get("feat_serie_limitee", []): pats.append((lg, p))
n = 0
for r in rows:
    if r.get("feat_serie_limitee") is True: continue
    de = r.get("de") or ""
    for lg, p in pats:
        m = re.search(p, de, re.I)
        if m:
            n += 1
            if n <= 15:
                s = max(0, m.start() - 45); print("  [%s] %-22s ...%s..." % (lg, str(r.get("mo"))[:22], " ".join(de[s:m.end()+45].split())))
            break
print("")
print("  total nouveaux serie_limitee : %d" % n)
