"""
Backfill tuned_by — sets cars.tuned_by from sub-brand patterns + aftermarket
preparators. Idempotent (only updates WHERE tuned_by IS NULL).

Run weekly via cron de sécurité (Monday 10:00 UTC) to catch any car
inserted without tuned_by (fallback if pipeline scraper missed it).

Mirrors the SQL of the initial backfill executed 2026-05-09.
"""
from __future__ import annotations
import os
import sys
import time
from typing import Tuple
import psycopg2
from dotenv import load_dotenv

# Load .env from repo root (memory convention: load_dotenv finds frame caller)
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
if not DATABASE_URL:
    sys.exit('FATAL: DATABASE_URL or SUPABASE_DB_URL not set')

# (description, sql_update_statement)
PATTERNS: list[Tuple[str, str]] = [
    # ===== Sub-brands officielles =====
    ('AMG (Mercedes-Benz)', """
        UPDATE cars SET tuned_by='AMG'
        WHERE status='active' AND tuned_by IS NULL AND mk='Mercedes-Benz'
          AND (mo ~* '\\mamg\\M' OR de ~* '\\mamg\\M')
    """),
    ('M (BMW)', """
        UPDATE cars SET tuned_by='M'
        WHERE status='active' AND tuned_by IS NULL AND mk='BMW'
          AND (mo ~* '\\mM\\s?[2-8]\\M' OR mo ~* '\\mM[\\s-]?(Sport|Perform|Pakket|Pack)\\M' OR mo ~* '\\mM-Sport\\M')
    """),
    ('RS (Audi)', """
        UPDATE cars SET tuned_by='RS'
        WHERE status='active' AND tuned_by IS NULL AND mk='Audi'
          AND mo ~* '\\m(RS|RSQ)\\d?\\M'
    """),
    ('S (Audi)', """
        UPDATE cars SET tuned_by='S'
        WHERE status='active' AND tuned_by IS NULL AND mk='Audi'
          AND (mo ~* '\\mS\\d\\M' OR mo ~* '\\mSQ\\d\\M')
    """),
    ('JCW (Mini)', """
        UPDATE cars SET tuned_by='JCW'
        WHERE status='active' AND tuned_by IS NULL AND mk='Mini'
          AND (mo ~* '\\mjcw\\M' OR mo ~* '\\m(john\\s)?cooper\\sworks\\M')
    """),
    ('Nismo', """
        UPDATE cars SET tuned_by='Nismo'
        WHERE status='active' AND tuned_by IS NULL AND mk='Nissan'
          AND (mo ~* '\\mnismo\\M' OR de ~* '\\mnismo\\M')
    """),
    ('STI', """
        UPDATE cars SET tuned_by='STI'
        WHERE status='active' AND tuned_by IS NULL AND mk='Subaru'
          AND (mo ~* '\\msti\\M' OR de ~* '\\msti\\M')
    """),
    ('TRD', """
        UPDATE cars SET tuned_by='TRD'
        WHERE status='active' AND tuned_by IS NULL AND mk IN ('Toyota','Lexus')
          AND (mo ~* '\\mtrd\\M' OR de ~* '\\mtrd\\M')
    """),
    ('SRT', """
        UPDATE cars SET tuned_by='SRT'
        WHERE status='active' AND tuned_by IS NULL AND mk IN ('Dodge','Chrysler','Jeep','Ram')
          AND (mo ~* '\\msrt[0-9]?\\M' OR de ~* '\\msrt[0-9]?\\M')
    """),
    # ===== Aftermarket distinctifs =====
    ('Brabus', """
        UPDATE cars SET tuned_by='Brabus'
        WHERE status='active' AND tuned_by IS NULL
          AND (mo ~* '\\mbrabus\\M' OR de ~* '\\mbrabus\\M')
    """),
    ('Mansory', """
        UPDATE cars SET tuned_by='Mansory'
        WHERE status='active' AND tuned_by IS NULL
          AND (mo ~* '\\mmansory\\M' OR de ~* '\\mmansory\\M')
    """),
    ('Liberty Walk', """
        UPDATE cars SET tuned_by='Liberty Walk'
        WHERE status='active' AND tuned_by IS NULL
          AND (mo ~* '\\m(liberty[\\s-]walk|lbwk|lb[\\s-]works?)\\M' OR de ~* '\\m(liberty[\\s-]walk|lbwk)\\M')
    """),
    ('Rauh-Welt', """
        UPDATE cars SET tuned_by='Rauh-Welt'
        WHERE status='active' AND tuned_by IS NULL AND mk='Porsche'
          AND (mo ~* '\\m(rwb|rauh[\\s-]welt)\\M' OR de ~* '\\m(rwb|rauh[\\s-]welt)\\M')
    """),
    ('TechArt', """
        UPDATE cars SET tuned_by='TechArt'
        WHERE status='active' AND tuned_by IS NULL AND mk='Porsche'
          AND (mo ~* '\\mtechart\\M' OR de ~* '\\mtechart\\M')
    """),
    ('Manthey-Racing', """
        UPDATE cars SET tuned_by='Manthey-Racing'
        WHERE status='active' AND tuned_by IS NULL AND mk='Porsche'
          AND (mo ~* '\\mmanthey\\M' OR de ~* '\\mmanthey\\M')
    """),
    ('Singer (Porsche)', """
        UPDATE cars SET tuned_by='Singer'
        WHERE status='active' AND tuned_by IS NULL AND mk='Porsche'
          AND (mo ~* '\\msinger\\M' OR de ~* '\\msinger\\M')
    """),
    ('RUF (Porsche)', """
        UPDATE cars SET tuned_by='RUF'
        WHERE status='active' AND tuned_by IS NULL AND mk='Porsche'
          AND (mo ~* '\\m(ruf|yellowbird|ctr[0-9]?)\\M' OR de ~* '\\m(ruf|yellowbird|ctr[0-9]?)\\M')
    """),
    # ===== Aftermarket Mercedes/BMW/VAG =====
    ('Lorinser', "UPDATE cars SET tuned_by='Lorinser' WHERE status='active' AND tuned_by IS NULL AND mk='Mercedes-Benz' AND (mo ~* '\\mlorinser\\M' OR de ~* '\\mlorinser\\M')"),
    ('Carlsson', "UPDATE cars SET tuned_by='Carlsson' WHERE status='active' AND tuned_by IS NULL AND mk IN ('Mercedes-Benz','Smart') AND (mo ~* '\\mcarlsson\\M' OR de ~* '\\mcarlsson\\M')"),
    ('Renntech', "UPDATE cars SET tuned_by='Renntech' WHERE status='active' AND tuned_by IS NULL AND mk='Mercedes-Benz' AND (mo ~* '\\mrenntech\\M' OR de ~* '\\mrenntech\\M')"),
    ('AC Schnitzer', "UPDATE cars SET tuned_by='AC Schnitzer' WHERE status='active' AND tuned_by IS NULL AND mk IN ('BMW','Mini','Land Rover') AND (mo ~* '\\m(ac.schnitzer|acs)\\M' OR de ~* '\\m(ac.schnitzer|acs)\\M')"),
    ('Hamann', "UPDATE cars SET tuned_by='Hamann' WHERE status='active' AND tuned_by IS NULL AND (mo ~* '\\mhamann\\M' OR de ~* '\\mhamann\\M')"),
    ('Manhart', "UPDATE cars SET tuned_by='Manhart' WHERE status='active' AND tuned_by IS NULL AND mk IN ('BMW','Mini','Porsche') AND (mo ~* '\\mmanhart\\M' OR de ~* '\\mmanhart\\M')"),
    ('Dinan', "UPDATE cars SET tuned_by='Dinan' WHERE status='active' AND tuned_by IS NULL AND mk='BMW' AND (mo ~* '\\mdinan\\M' OR de ~* '\\mdinan\\M')"),
    ('ABT Sportsline', "UPDATE cars SET tuned_by='ABT Sportsline' WHERE status='active' AND tuned_by IS NULL AND mk IN ('Audi','Volkswagen','SEAT','Škoda','Porsche') AND (mo ~* '\\mabt\\M' OR de ~* '\\mabt sportsline\\M')"),
    ('MTM', "UPDATE cars SET tuned_by='MTM' WHERE status='active' AND tuned_by IS NULL AND mk IN ('Audi','Volkswagen','Lamborghini','Bentley','Porsche') AND (mo ~* '\\mmtm\\M' OR de ~* '\\mmtm bayreuth\\M')"),
    ('Novitec', "UPDATE cars SET tuned_by='Novitec' WHERE status='active' AND tuned_by IS NULL AND (mo ~* '\\m(novitec|spofec|torado|tridente|rosso)\\M' OR de ~* '\\mnovitec\\M')"),
    ('Vorsteiner', "UPDATE cars SET tuned_by='Vorsteiner' WHERE status='active' AND tuned_by IS NULL AND (mo ~* '\\mvorsteiner\\M' OR de ~* '\\mvorsteiner\\M')"),
    ('Overfinch', "UPDATE cars SET tuned_by='Overfinch' WHERE status='active' AND tuned_by IS NULL AND mk='Land Rover' AND (mo ~* '\\moverfinch\\M' OR de ~* '\\moverfinch\\M')"),
    ('Roush', "UPDATE cars SET tuned_by='Roush' WHERE status='active' AND tuned_by IS NULL AND mk='Ford' AND (mo ~* '\\mroush\\M' OR de ~* '\\mroush\\M')"),
    ('Heico Sportiv', "UPDATE cars SET tuned_by='Heico Sportiv' WHERE status='active' AND tuned_by IS NULL AND mk='Volvo' AND (mo ~* '\\mheico\\M' OR de ~* '\\mheico\\M')"),
]


def main():
    t0 = time.time()
    print(f'[backfill_tuned_by] Connecting to DB...', flush=True)
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Pre-state stats
    cur.execute("SELECT COUNT(*) FROM cars WHERE status='active'")
    total_active = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cars WHERE status='active' AND tuned_by IS NOT NULL")
    pre_set = cur.fetchone()[0]
    print(f'[backfill_tuned_by] Pre-run: {pre_set}/{total_active} cars have tuned_by ({100*pre_set/total_active:.1f}%)', flush=True)

    total_new = 0
    for description, sql in PATTERNS:
        cur.execute(sql)
        n = cur.rowcount
        if n > 0:
            print(f'  + {description}: {n} cars', flush=True)
        total_new += n

    # Post-state stats
    cur.execute("SELECT COUNT(*) FROM cars WHERE status='active' AND tuned_by IS NOT NULL")
    post_set = cur.fetchone()[0]
    duration = time.time() - t0
    print(f'\n[backfill_tuned_by] Done in {duration:.1f}s', flush=True)
    print(f'[backfill_tuned_by] Post-run: {post_set}/{total_active} cars have tuned_by ({100*post_set/total_active:.1f}%)', flush=True)
    print(f'[backfill_tuned_by] Newly set this run: {total_new}', flush=True)

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
