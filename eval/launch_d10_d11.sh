#!/bin/sh
# D10/D11 runs (exploratory). Order chosen so that the cheapest, highest-value runs finish first.
cd "$(dirname "$0")/.."
R="env PYTHONPATH=. .venv/bin/python eval/run_agents.py --require-proposals"
H=claude-haiku-5-5; S=claude-sonnet-5-5
$R --exp e5wid_haiku --injection widen --conditions TSE --widen judge --cells $H/react,$H/lg --workers 4
$R --exp e5wid_sonnet --injection widen --conditions TSE --widen judge --cells $S/react --workers 4
$R --exp abl_haiku --subset eval/subset_ablation_200.txt --conditions TSE --variant tse --widen judge --cells $H/react,$H/lg --workers 4
$R --exp b3w_sonnet --subset eval/subset_ablation_200.txt --conditions TSE --variant tse --widen judge --cells $S/react --workers 4
$R --exp e2_haiku --conditions TSE --variant tse_haiku --widen auto --cells $H/react,$H/lg --workers 4
$R --exp e2_sonnet_r --subset eval/subset_b1_500.txt --conditions TSE --variant tse_haiku --widen auto --cells $S/react --workers 4
echo "D10/D11 done $(date)"
