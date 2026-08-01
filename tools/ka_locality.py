import re

RX = re.compile(r"^\s*(\d{5})\s+(.+?)\s*$")

def parse_locality(raw):
    if not raw:
        return None
    s = " ".join(str(raw).split())
    m = RX.match(s)
    if not m:
        return None
    plz, rest = m.group(1), m.group(2)
    if " - " in rest:
        region, city = rest.split(" - ", 1)
    else:
        region, city = rest, rest
    city = city.strip(" ,-")
    region = region.strip(" ,-")
    if not city:
        return None
    return {"plz": plz, "region": region, "city": city}

if __name__ == "__main__":
    CASES = [
        ("86633 Bayern - Neuburg a.d. Donau", "Neuburg a.d. Donau", "Bayern", "86633"),
        ("88045 Baden-Württemberg - Friedrichshafen", "Friedrichshafen", "Baden-Württemberg", "88045"),
        ("30890 Niedersachsen - Barsinghausen", "Barsinghausen", "Niedersachsen", "30890"),
        ("10115 Berlin", "Berlin", "Berlin", "10115"),
        ("78628 Baden-Württemberg - Rottweil", "Rottweil", "Baden-Württemberg", "78628"),
        ("Allemagne", None, None, None),
        ("", None, None, None),
        (None, None, None, None),
    ]
    ok = 0
    for raw, city, region, plz in CASES:
        got = parse_locality(raw)
        if city is None:
            good = got is None
            shown = "None"
        else:
            good = bool(got) and got["city"] == city and got["region"] == region and got["plz"] == plz
            shown = "%s | %s | %s" % (got["plz"], got["region"], got["city"]) if got else "None"
        ok += good
        print("  %s  %-45r -> %s" % ("ok " if good else "KO ", raw, shown))
    print("")
    print("  %d/%d" % (ok, len(CASES)))
