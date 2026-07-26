#!/bin/zsh
# run_market_scrapers.sh — full-auto marketplaces via CDP (mobile.de + kleinanzeigen + C&C).
set -u
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="$HOME/.chrome-scraper"
DIR="$HOME/Code/autoradar/scraper"
LOG="$DIR/logs/market_cron.log"
mkdir -p "$DIR/logs"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') run =====" >> "$LOG"

# Chrome debug up ? sinon on le lance (headless new).
if ! curl -s http://localhost:9222/json/version >/dev/null 2>&1 ; then
  echo "[wrap] lance Chrome debug…" >> "$LOG"
  "$CHROME" --remote-debugging-port=9222 --user-data-dir="$PROFILE" \
            --headless=new --no-first-run --no-default-browser-check >/dev/null 2>&1 &
  sleep 10
fi

cd "$DIR" || exit 1
source venv/bin/activate

# —— Mets TES recherches ici (filtre + tri « plus récentes ») ——
MOBILE_URL="https://www.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&s=Car&sb=rel&od=down"
KA_URL="https://www.kleinanzeigen.de/s-autos/sortierung:neuste/preis:5000:/c216+autos.schaden_s:nein+options:autos.full_service_history_b"
CC_URL="https://www.carandclassic.com/search?category=1&sort=newest"

echo "[wrap] mobile.de…" >> "$LOG"
python3 scrape_mobilede_cdp.py --apply --max-pages 40 --url "$MOBILE_URL" >> "$LOG" 2>&1
sleep 20
echo "[wrap] kleinanzeigen…" >> "$LOG"
python3 scrape_kleinanzeigen_cdp.py --apply --max-pages 40 --url "$KA_URL" >> "$LOG" 2>&1
# carandclassic : service worker hostile en CDP -> reste sur le bookmarklet (semi-auto).
# python3 scrape_carandclassic_cdp.py --apply --max-pages 60 --url "$CC_URL" >> "$LOG" 2>&1

# —— Rafraîchit le bandeau « Le marché » (médiane/marchands/pays/cette-semaine)
#    directement, indépendant de GitHub Actions. Lecture live de cars, ~30s.
echo "[wrap] refresh bandeau marché…" >> "$LOG"
python3 -u -c "import os; from dotenv import load_dotenv; load_dotenv('$DIR/.env'); from supabase import create_client; d=create_client(os.environ['SUPABASE_URL'],os.environ['SUPABASE_SERVICE_KEY']).rpc('refresh_market_snapshot').execute().data; print('[snapshot]',d)" >> "$LOG" 2>&1

echo "[wrap] fini $(date '+%H:%M:%S')" >> "$LOG"
