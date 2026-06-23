#!/usr/bin/env bash
cd ~/Code/autoradar/scraper || exit 1
LOG=/tmp/auto_backfill_llm.log
if pgrep -f "scripts/backfill_llm.py" > /dev/null 2>&1; then
  echo "$(date) -- backfill deja en cours, skip" >> "$LOG"; exit 0
fi
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "$(date) -- Ollama down, demarrage app Ollama..." >> "$LOG"
  open -a Ollama
  for i in $(seq 1 30); do
    sleep 2
    curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && break
  done
fi
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "$(date) -- Ollama injoignable apres 60s, skip" >> "$LOG"; exit 0
fi
source venv/bin/activate 2>/dev/null || { echo "$(date) -- venv KO" >> "$LOG"; exit 1; }
echo "=== AUTO BACKFILL START $(date) ===" >> "$LOG"
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b AUTORADAR_LLM_HOOK_ENABLED=true python -u scripts/backfill_llm.py --max 2000 >> "$LOG" 2>&1
echo "=== AUTO BACKFILL END $(date) ===" >> "$LOG"
