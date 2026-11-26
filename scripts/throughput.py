import json, time, urllib.request, sys
schema=json.load(open('data/raw/bird_minidev/postgresql.json'))['formula_1']
prompt=f"Schema:\n{schema}\n\nQuestion: Which driver won the most races in 2009? Write one PostgreSQL query. Reply with SQL only."
for m in sys.argv[1:]:
    body=json.dumps({"model":m,"messages":[{"role":"user","content":prompt}],"stream":False,"options":{"temperature":0,"num_ctx":16384},"think":False}).encode()
    for i in range(2):
        t=time.time(); r=json.load(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat",body,{'Content-Type':'application/json'}),timeout=600))
        print(m, i, f"{time.time()-t:.1f}s prompt_tok={r.get('prompt_eval_count')} pe={r.get('prompt_eval_duration',0)/1e9:.1f}s out_tok={r.get('eval_count')} gen={r.get('eval_duration',0)/1e9:.1f}s", flush=True)
