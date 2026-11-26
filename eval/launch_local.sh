#!/bin/sh
# Open-weight arm (deviation D5): starts after GPU scope inference finishes; stopped at the preregistered deadline.
cd "$(dirname "$0")/.."
while kill -0 2332 2>/dev/null; do sleep 30; done
PYTHONPATH=. .venv/bin/python eval/run_agents.py --require-proposals --keep-order --exp e2_local \
  --subset eval/subset_local_200_order.txt --conditions B0,B3,TSE \
  --cells qwen3:8b/react,qwen3:8b/lg,qwen2.5-coder:7b/react --workers 2 --out eval/results/runs_e2_local.jsonl &
P=$!
DEADLINE=$(date -j -f "%Y-%m-%d %H:%M" "2026-11-27 12:00" +%s)
while kill -0 $P 2>/dev/null; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then echo "deadline reached $(date)"; kill $P; break; fi
  sleep 30
done
wait $P; echo "local arm ended $(date)"
