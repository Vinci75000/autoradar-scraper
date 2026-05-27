# Sources archivées — Vue Enchères Phase 2

## bonhams_online / themarket.co.uk
**Archivé 27/05/26.**

**Raison : opt-out TDM machine-readable formel.**

robots.txt expose un Content-Signal Cloudflare explicite :
- `Content-Signal: search=yes, ai-train=no` (préambule cite Art. 4 dir UE 2019/790)
- `User-agent: ClaudeBot Disallow: /` + Disallow exhaustif des AI bots
  (GPTBot, Bytespider, CCBot, Applebot-Extended, Google-Extended, meta-externalagent)

Bien que Carnet ne soit pas littéralement "ClaudeBot", notre pipeline aval
enrichit chaque lot via Claude API (`extract_features v2 LLM`). C'est
techniquement un usage `ai-input` (RAG/grounding/temps réel) qui rentre dans
l'esprit du Disallow ClaudeBot.

Position Carnet : asso loi 1901 EU, "Référentiel Transparence" → on doit
être exemplaire. On respecte l'opt-out machine-readable, on archive.

Code/tests/fixture conservés en `.bak` pour traçabilité, pas en prod.

---

## getyourclassic.com
**Archivé 27/05/26** (différent — produit pas Vue Enchères).

Plateforme showroom fixed-price (WooCommerce). Leurs enchères vivent en
réalité sur classictrader.com/uk/cars/auctions, déjà scrapé via
`extractors/classictrader.py`. Code Vague 1 conservé pour future Vue Affût
(showroom marketplace, sprint dédié post-MVP Enchères).

