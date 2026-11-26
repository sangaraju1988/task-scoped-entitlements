#!/bin/sh
# Phase A: every scope-dependent agent run (starts after main proposals exist). Two parallel lanes.
cd "$(dirname "$0")/.."
R="env PYTHONPATH=. .venv/bin/python eval/run_agents.py --require-proposals"
H=claude-haiku-5-5; S=claude-sonnet-5-5
( $R --exp e2_haiku --conditions B3,TSE --cells $H/react,$H/lg --workers 4
  $R --exp e5ctx_haiku --injection context --conditions B3,TSE --cells $H/react,$H/lg --workers 4
  $R --exp e5wid_haiku --injection widen --conditions TSE --widen auto --cells $H/react,$H/lg --workers 4
  $R --exp e5wid_haiku --injection widen --conditions TSE --widen strict --cells $H/react,$H/lg --workers 4
  $R --exp e5db_haiku --injection dbfield --conditions B3,TSE --cells $H/react,$H/lg --workers 4
  $R --exp e2np_haiku --set nonpermitted --conditions TSE --cells $H/react,$H/lg --workers 4
  for v in tse_k0 tse_k2; do $R --exp abl_haiku --variant $v --conditions TSE --subset eval/subset_ablation_200.txt --cells $H/react,$H/lg --workers 4; done
  $R --exp abl_haiku --variant tse --widen deny --conditions TSE --subset eval/subset_ablation_200.txt --cells $H/react,$H/lg --workers 4
  $R --exp abl_haiku --variant tse --widen strict --conditions TSE --subset eval/subset_ablation_200.txt --cells $H/react,$H/lg --workers 4
  $R --exp e5ctx_haiku_deny --injection context --conditions TSE --widen deny --cells $H/react,$H/lg --workers 4
  $R --exp seeds_haiku --conditions B0,TSE --seeds 1,2,3 --subset eval/subset_seeds_100.txt --cells $H/react --workers 4
) > logs/phase_a_haiku.log 2>&1 &
( $R --exp e2_sonnet_r --conditions B3,TSE --cells $S/react --workers 4
  $R --exp e5ctx_sonnet --injection context --conditions B3,TSE --cells $S/react --workers 4
  $R --exp e5wid_sonnet --injection widen --conditions TSE --widen auto --cells $S/react --workers 4
  $R --exp e5wid_sonnet --injection widen --conditions TSE --widen strict --cells $S/react --workers 4
  $R --exp e5ctx_sonnet_deny --injection context --conditions TSE --widen deny --cells $S/react --workers 4
) > logs/phase_a_sonnet.log 2>&1 &
wait
echo "phase A done $(date)"
