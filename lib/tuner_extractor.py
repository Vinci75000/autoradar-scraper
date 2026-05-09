"""
Tuner extractor — détecte le préparateur (sub-brand officielle ou aftermarket)
à partir des champs mk/mo/de d'une voiture.

Usage:
    from scraper.lib.tuner_extractor import extract_tuner
    tuned_by = extract_tuner(mk='Mercedes-Benz', mo='C 63 AMG', de='...')
    # -> 'AMG'

Patterns alignés avec le SQL backfill (refresh hebdo via cron de sécurité).
"""
from __future__ import annotations
import re
from typing import Optional

# (tuner_name, regex_pattern, allowed_mks_or_None_for_all)
# Ordre = priorité (premier match wins)
_PATTERNS: list[tuple[str, str, Optional[set[str]]]] = [
    # ===== Sub-brands officielles =====
    ('AMG',             r'\bamg\b',                                      {'Mercedes-Benz'}),
    ('M',               r'\bM\s?[2-8]\b|\bM[\s-]?(Sport|Perform|Pakket|Pack)\b|\bM-Sport\b',
                                                                          {'BMW'}),
    ('RS',              r'\b(RS|RSQ)\d?\b',                              {'Audi'}),
    ('S',               r'\bS\d\b|\bSQ\d\b',                             {'Audi'}),
    ('JCW',             r'\bjcw\b|\b(john\s)?cooper\sworks\b',           {'Mini'}),
    ('Nismo',           r'\bnismo\b',                                    {'Nissan'}),
    ('STI',             r'\bsti\b',                                      {'Subaru'}),
    ('TRD',             r'\btrd\b',                                      {'Toyota','Lexus'}),
    ('SRT',             r'\bsrt[0-9]?\b',                                {'Dodge','Chrysler','Jeep','Ram'}),
    ('N',               r'\b(i[23]0\s?N|veloster\s?N|kona\s?N|ioniq\s?5\s?N)\b', {'Hyundai'}),
    ('Renault Sport',   r'\b(R\.?S\.?|trophy[\s-]r|megane\s?rs|clio\s?rs)\b|renault sport',
                                                                          {'Renault'}),
    ('Peugeot Sport',   r'\b(GTi|PSE)\b|peugeot sport',                  {'Peugeot'}),
    ('Mopar',           r'\bmopar\b',                                    {'Dodge','Chrysler','Jeep','Ram'}),
    ('Ralliart',        r'\bralliart\b',                                 {'Mitsubishi'}),

    # ===== Aftermarket distinctifs (multi-mk) =====
    ('Brabus',          r'\bbrabus\b',                                   None),
    ('Mansory',         r'\bmansory\b',                                  None),
    ('Liberty Walk',    r'\b(liberty[\s-]walk|lbwk|lb[\s-]works?)\b',    None),
    ('Rauh-Welt',       r'\b(rwb|rauh[\s-]welt)\b',                      {'Porsche'}),
    ('TechArt',         r'\btechart\b',                                  {'Porsche'}),
    ('Gemballa',        r'\bgemballa\b',                                 None),
    ('Manthey-Racing',  r'\bmanthey\b',                                  {'Porsche'}),
    ('Singer',          r'\bsinger\b',                                   {'Porsche'}),
    ('RUF',             r'\b(ruf|yellowbird|ctr[0-9]?)\b',               {'Porsche'}),

    # ===== Aftermarket Mercedes =====
    ('Lorinser',        r'\blorinser\b',                                 {'Mercedes-Benz'}),
    ('Carlsson',        r'\bcarlsson\b',                                 {'Mercedes-Benz','Smart'}),
    ('Renntech',        r'\brenntech\b',                                 {'Mercedes-Benz'}),
    ('Kleemann',        r'\bkleemann\b',                                 {'Mercedes-Benz'}),
    ('Posaidon',        r'\bposaidon\b',                                 {'Mercedes-Benz'}),

    # ===== Aftermarket BMW =====
    ('AC Schnitzer',    r'\b(ac.schnitzer|acs)\b',                       {'BMW','Mini','Land Rover'}),
    ('Hamann',          r'\bhamann\b',                                   None),
    ('Hartge',          r'\bhartge\b',                                   {'BMW','Mini','Land Rover'}),
    ('G-Power',         r'\bg.power\b',                                  {'BMW'}),
    ('Manhart',         r'\bmanhart\b',                                  {'BMW','Mini','Porsche'}),
    ('Dinan',           r'\bdinan\b',                                    {'BMW'}),

    # ===== Aftermarket VAG =====
    ('ABT Sportsline',  r'\babt\b',                                      {'Audi','Volkswagen','SEAT','Škoda','Porsche'}),
    ('MTM',             r'\bmtm\b',                                      {'Audi','Volkswagen','Lamborghini','Bentley','Porsche'}),

    # ===== Aftermarket Italian/Lambo =====
    ('Novitec',         r'\b(novitec|spofec|torado|tridente|rosso)\b',   None),
    ('DMC',             r'\bdmc\b',                                      {'Lamborghini','McLaren','Ferrari'}),
    ('Vorsteiner',      r'\bvorsteiner\b',                               None),

    # ===== Aftermarket Range Rover =====
    ('Overfinch',       r'\boverfinch\b',                                {'Land Rover'}),
    ('Kahn Design',     r'\b(kahn|project kahn)\b',                      None),
    ('Startech',        r'\bstartech\b',                                 None),

    # ===== Aftermarket US =====
    ('Roush',           r'\broush\b',                                    {'Ford'}),
    ('Lingenfelter',    r'\blingenfelter\b',                             None),

    # ===== Aftermarket Japan =====
    ('Mugen',           r'\bmugen\b',                                    {'Honda'}),
    ('Spoon Sports',    r'\bspoon\b',                                    {'Honda'}),
    ('HKS',             r'\bhks\b',                                      None),
    ('Toms',            r'\btoms\b',                                     {'Toyota','Lexus'}),
    ('Veilside',        r'\bveilside\b',                                 None),

    # ===== Volvo officiel =====
    ('Heico Sportiv',   r'\bheico\b',                                    {'Volvo'}),
]

# Mk standalone tuners -> tuned_by = mk
_MK_STANDALONE = {
    'Alpina','RUF','Singer','Brabus','Shelby','Saleen','Callaway','Hennessey',
    'Cupra','Polestar','Abarth','Wiesmann','W Motors','Zenvo','Spania GTA',
    'Bufori','PGO','Secma','Devalliet','Kimera','Totem','TWR','Gunther Werks',
    'Eagle','David Brown','Lunaz','Nardone','Theon Design','Emory','Twisted',
    'Gateway Bronco','Icon 4x4','Classic Recreations','Everrati','Redux',
    'Prodrive','Evoluto','Erreerre','Thornley Kelham','Kalmar','Alfaholics',
    'Ginetta','Marcos','Radical','SCG','Glickenhaus','Hopium','Bizzarrini',
    'De Tomaso','Iso','Iso Rivolta','Bristol','Jensen','Jensen-Healey',
    'Hispano-Suiza','Cisitalia','Tucker','Auburn','Cord','Duesenberg','Stutz',
    'Pierce-Arrow','Marmon','Auto Union','Brabham','Vanwall','BRM','Lola',
    'Cooper','Chevron','Chaparral','Saab','Talbot','Talbot-Lago','Delahaye',
    'Delage','Voisin','Facel Vega','OSCA','Panhard','Salmson','Hotchkiss',
    'Bugatti','TVR','Reliant','Daimler','Plymouth','Pontiac','Oldsmobile',
    'Mercury','Hummer','Holden','Rover','Daewoo','Edsel','Hudson','Studebaker',
    'LaSalle','Packard','Avanti','Maybach',
}

# Compile patterns once
_COMPILED = [(name, re.compile(pattern, re.IGNORECASE), brands)
             for name, pattern, brands in _PATTERNS]


def extract_tuner(mk: Optional[str],
                  mo: Optional[str],
                  de: Optional[str] = None) -> Optional[str]:
    """
    Détecte le tuner/préparateur d'une voiture.

    Priorité :
    1. mk standalone tuner (Alpina, RUF, Brabus...) -> return mk
    2. Sub-brand officielle / aftermarket via regex sur mo + de

    Args:
        mk: marque (ex. 'Mercedes-Benz')
        mo: modèle (ex. 'C 63 AMG')
        de: description (optional, plus de contexte)

    Returns:
        Tuner name ou None si aucun match.
    """
    if mk and mk in _MK_STANDALONE:
        return mk

    text = ' '.join(filter(None, [mo or '', de or '']))
    if not text.strip():
        return None

    for tuner_name, pattern, allowed_mks in _COMPILED:
        if allowed_mks is not None and mk not in allowed_mks:
            continue
        if pattern.search(text):
            return tuner_name

    return None


if __name__ == '__main__':
    cases = [
        (('Mercedes-Benz', 'C 63 AMG', None),         'AMG'),
        (('BMW',           'M3 Competition', None),    'M'),
        (('Audi',          'RS6 Avant', None),         'RS'),
        (('Audi',          'SQ5 TFSI', None),          'S'),
        (('Mini',          'JCW Cabrio', None),        'JCW'),
        (('Porsche',       '911 GT3 RS Manthey', None),'Manthey-Racing'),
        (('Porsche',       '911 Singer DLS', None),    'Singer'),
        (('Mercedes-Benz', 'G500 Brabus 800', None),   'AMG'),
        (('Mercedes-Benz', 'G500', 'Brabus 800 widebody kit'), 'Brabus'),
        (('Smart',         'Fortwo Brabus', None),     'Brabus'),
        (('Alpina',        'B7', None),                'Alpina'),
        (('RUF',           'CTR Yellowbird', None),    'RUF'),
        (('Toyota',        'Corolla', None),            None),
        (('Audi',          'A4', None),                 None),
    ]
    fails = 0
    for (args, expected) in cases:
        got = extract_tuner(*args)
        ok = got == expected
        mark = 'OK ' if ok else 'FAIL'
        print(f"[{mark}] extract_tuner{args} = {got!r} (expected {expected!r})")
        if not ok:
            fails += 1
    print(f"\n{len(cases)-fails}/{len(cases)} tests passed")
