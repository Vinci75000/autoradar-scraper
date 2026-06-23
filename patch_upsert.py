"""Patch insert_car (scraper.py) : transforme le skip L1 src_url en UPSERT.

Sur match src_url (meme annonce deja en base), au lieu de skipper :
  - rafraichit last_seen_at (nourrit clean_expired, evite le re-ping a 7j)
  - met px a jour si le prix a change (corpus a jour cote prix)
Ne touche NI price_log NI times_seen -> aucun risque de doubler un trigger DB.
La dedup L2 (fingerprint cross-source) reste intacte.

Idempotent + assert + compile. A lancer depuis la racine du repo scraper.
    python3 patch_upsert.py
"""
import pathlib
import py_compile

p = pathlib.Path("scraper.py")
s = p.read_text()

old = (
    "    if is_duplicate(db, car):\n"
    "        log.info(f'Duplicate: {car.mk} {car.mo} {car.yr} \u2014 skipped')\n"
    "        return None\n"
)
new = (
    "    # L1 src_url \u2014 meme annonce deja en base : on rafraichit (prix + last_seen_at)\n"
    "    # au lieu de skipper sec. Garde le prix a jour + nourrit le wash (clean_expired).\n"
    "    _exist = (db.table('cars')\n"
    "                .select('id, px')\n"
    "                .eq('src_url', car.src_url)\n"
    "                .limit(1)\n"
    "                .execute())\n"
    "    if _exist.data:\n"
    "        _rid = _exist.data[0]['id']\n"
    "        _old_px = _exist.data[0].get('px')\n"
    "        _upd = {'last_seen_at': datetime.utcnow().isoformat() + 'Z'}\n"
    "        if car.px is not None and car.px != _old_px:\n"
    "            _upd['px'] = car.px\n"
    "            log.info(f'\u21bb Updated: {car.mk} {car.mo} {car.yr} \u2014 {_old_px} \u2192 {car.px}\u20ac')\n"
    "        else:\n"
    "            log.info(f'\u21bb Seen: {car.mk} {car.mo} {car.yr} \u2014 last_seen refreshed')\n"
    "        db.table('cars').update(_upd).eq('id', _rid).execute()\n"
    "        return None\n"
    "\n"
    "    if is_duplicate(db, car):\n"
    "        log.info(f'Duplicate: {car.mk} {car.mo} {car.yr} \u2014 skipped')\n"
    "        return None\n"
)

if "_exist = (db.table('cars')" in s or "\u21bb Updated" in s:
    print("  upsert-patch : deja applique")
else:
    assert s.count(old) == 1, "anchor x%d (le bloc is_duplicate a change ?)" % s.count(old)
    s = s.replace(old, new)
    p.write_text(s)
    print("  upsert-patch : applique (L1 src_url -> upsert px + last_seen_at)")

py_compile.compile("scraper.py", doraise=True)
print("  compile OK")
