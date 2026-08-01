import sys; sys.path.insert(0,".")
exec(open("scripts/bf_ml.py").read().split("sel = ")[0].replace("Path(__file__).resolve().parent.parent","Path(\".\").resolve()"))
import feature_extractor as fe
from collections import Counter
APPLY2 = "--apply" in sys.argv
rows=[];last=""
while True:
    p={"select":"id,mo,de,models_canonical(rarity_tier)","status":"eq.active","feat_serie_limitee":"is.true","de":"not.is.null","order":"id.asc","limit":"1000"}
    if last: p["id"]="gt."+last
    b=get(p)
    if not b: break
    rows+=b; last=b[-1]["id"]
    if len(b)<1000: break
todo=[]; c=Counter()
for r in rows:
    de=(r.get("de") or "")
    if len(de.strip())<12: c["desc_courte"]+=1; continue
    if fe.extract_features(description=de,title=r.get("mo") or "").get("feat_serie_limitee") is True: c["garde_texte"]+=1; continue
    mc=r.get("models_canonical") or {}
    t=(mc.get("rarity_tier") if isinstance(mc,dict) else None) or ""
    if t in ("ICONE","ICÔNE","REFERENCE","RÉFÉRENCE"): c["garde_rare"]+=1; continue
    todo.append(r["id"]); c["a_corriger"]+=1
print("serie_limitee=true : %d" % len(rows))
for k in ("garde_texte","garde_rare","desc_courte","a_corriger"): print("  %-14s %5d" % (k, c[k]))
if not APPLY2:
    print("")
    print("DRY-RUN — --apply pour passer les %d a false." % len(todo))
    sys.exit(0)
done=fail=0
for i,cid in enumerate(todo,1):
    if patch(cid, {"feat_serie_limitee": False}): done+=1
    else: fail+=1
    if i % 200 == 0: print("  ... %d/%d" % (i,len(todo))); time.sleep(3)
print("  corrigees : %d · echecs : %d" % (done,fail))
