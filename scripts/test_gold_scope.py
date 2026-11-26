import json, collections, traceback
from tse import semantic_layer, gold_scope
ok=0; fail=collections.Counter(); ex=[]
tasks=[json.loads(l) for l in open('data/tasks/tasks.jsonl')]
for t in tasks:
    sl=semantic_layer.get(t['pgdb'],t['dataset'],t['db_id'])
    try:
        s=gold_scope.extract(t['gold_sql'],sl); ok+=1
        if len(ex)<4 and t['dataset']=='bird': ex.append((t['gold_sql'][:200], s.to_json()))
    except Exception as e:
        fail[type(e).__name__+':'+str(e)[:80]]+=1
print('ok',ok,'fail',sum(fail.values())); print(fail.most_common(5))
for e in ex: print(e[0]); print(json.dumps(e[1])[:600]); print()
