import json, time, urllib.request, sys, concurrent.futures as cf
m=sys.argv[1]; P=int(sys.argv[2])
schema=json.load(open('data/raw/bird_minidev/postgresql.json'))['formula_1']
qs=["Which driver won the most races in 2009?","How many races were held in 2010?","List circuits in Italy.","Who had the fastest lap in race 18?","Which constructor has most points?","Name drivers born after 1990.","Average pit stop duration in 2011?","How many drivers are German?"]
def call(q):
    body=json.dumps({"model":m,"messages":[{"role":"system","content":"Schema:\n"+schema},{"role":"user","content":q+" Write one PostgreSQL query. SQL only."}],"stream":False,"options":{"temperature":0,"num_ctx":8192},"think":False}).encode()
    r=json.load(urllib.request.urlopen(urllib.request.Request("http://localhost:11500/api/chat",body,{'Content-Type':'application/json'}),timeout=900)); return r.get('eval_count',0)
call(qs[0])
t=time.time()
with cf.ThreadPoolExecutor(P) as ex: toks=list(ex.map(call,qs))
dt=time.time()-t; print(f"{m} P={P}: {len(qs)} calls in {dt:.1f}s -> {dt/len(qs):.1f}s/call, {sum(toks)/dt:.1f} tok/s")
