#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null
python -u bridge_cars_to_ref.py --apply --retry-none    # relie cars -> ref
python -u discover_new_models.py --apply --min 3         # nourrit le ref
python -u tag_car_generations.py --apply                 # tague cars.generation
python -u backfill_members.py --apply                    # rattrape membres + public
