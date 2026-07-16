#!/bin/zsh
# Cron LOCAL elferspot — les recentes uniquement.
# GitHub Actions est bloque par BunnyShield (403 sur IP datacenter) ; ce run
# tourne depuis l'IP residentielle du Mac, qui passe.
# .env est charge automatiquement par scraper.py (load_dotenv).
cd /Users/sylvain17/Code/autoradar/scraper || exit 1
exec caffeinate -i venv/bin/python run_generic.py \
  --slug elferspot --max-pages 4 --limit 150 --write
