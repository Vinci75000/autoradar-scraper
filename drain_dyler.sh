#!/usr/bin/env bash
cd ~/Code/autoradar/scraper || exit 1
echo "=== DRAIN v2 START $(date) ==="
for i in $(seq 1 20); do
  echo ""; echo "===== PASSE $i — $(date '+%H:%M:%S') ====="
  AUTORADAR_LLM_HOOK_ENABLED=false python3 -u scripts/run_dyler.py --limit 1500
  rc=$?
  if [ $rc -eq 42 ]; then echo "=== DONE: dyler draine — $(date) ==="; break; fi
  sleep 8
done
echo "=== DRAIN v2 END $(date) ==="
