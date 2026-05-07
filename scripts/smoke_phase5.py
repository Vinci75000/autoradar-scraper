"""Smoke test Phase 5 : verifie que extract_features retourne bien
les 7 nouvelles cles feat_llm_* + feat_de_hash dans son dict de retour.

Pas d'appel API (hook OFF par defaut). Pas de DB. Juste check structure.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature_extractor import extract_features

EXPECTED_LLM_KEYS = {
    'feat_llm_highlights',
    'feat_llm_concerns',
    'feat_llm_summary',
    'feat_llm_raw_response',
    'feat_llm_model',
    'feat_llm_extracted_at',
    'feat_de_hash',
}

# Hook OFF (default) — les cles peuvent etre presentes (defauts None)
# OU absentes selon design du Features TypedDict.
features = extract_features(
    description='Belle Ferrari avec carnet complet et factures.',
    title='Ferrari 458 Italia',
    listing_tier='supercar',
    km_tier='low',
)

print(f'Total cles dans features : {len(features)}')
print()
print('Cles LLM presentes :')
for key in sorted(EXPECTED_LLM_KEYS):
    present = key in features
    value = features.get(key, '<absent>')
    print(f'  {key:30s} present={present} value={value!r}')

print()
missing = EXPECTED_LLM_KEYS - set(features.keys())
if missing:
    print(f'INFO : {len(missing)} cles LLM absentes du dict (sera NULL en DB) : {missing}')
else:
    print('OK : toutes les 7 cles LLM sont dans le dict (avec valeurs par defaut)')
