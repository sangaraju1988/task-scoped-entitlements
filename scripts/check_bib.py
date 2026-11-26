"""Verify every bib entry: DOI resolves on Crossref (title+authors compared) or arXiv ID resolves on arXiv API."""
import re, json, sys, time, urllib.request, unicodedata
sys.path.insert(0,'scripts')
from arxiv_lookup import by_ids
H={'User-Agent':'tse-research-script/0.1'}
bib=open(sys.argv[1]).read()
entries=[(m.group(1),m.group(2),m.group(3)) for m in re.finditer(r'@(\w+)\{([^,\s]+),(.*?)(?=\n@|\Z)', bib, re.S)]
def field(body,name):
    m=re.search(name+r'\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}', body, re.S); return m.group(1) if m else None
def norm(s): return re.sub(r'[^a-z]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def latex_strip(s): return re.sub(r'\\[a-zA-Z]+|[{}\\\'"`~^]','',s or '')
rows=[]; bad=0
allax=sorted(set(re.findall(r'arXiv:(\d{4}\.\d{4,5})', bib)))
AX={p['id'].split('v')[0]:p for p in by_ids(allax)}
for typ,key,body in entries:
    doi=field(body,'doi'); hp=field(body,'howpublished') or ''; note=field(body,'note') or ''
    ax=re.search(r'arXiv:(\d{4}\.\d{4,5})', hp+' '+note)
    authors=[a.strip() for a in latex_strip(field(body,'author') or '').split(' and ')]
    fams=[norm(a.split(',')[0]) for a in authors if a and a!='others']
    title=latex_strip(field(body,'title'))
    if doi:
        try:
            m=json.load(urllib.request.urlopen(urllib.request.Request('https://api.crossref.org/works/'+doi,headers=H),timeout=60))['message']
            cr=[norm(a.get('family',a.get('name',''))) for a in m.get('author',[])]
            ct=m['title'][0]
            tok=lambda s:set(re.findall('[a-z]{4,}',latex_strip(s).lower()))
            tmatch=len(tok(title)&tok(ct))/max(1,len(tok(title)))
            miss=[f for f in fams if f not in cr and not any(f in c or c in f for c in cr)]
            status='OK' if tmatch>0.6 and (not miss or not cr) else 'CHECK'
            rows.append((key,'crossref',doi,status,f"title_overlap={tmatch:.2f} bib_not_in_crossref={miss} crossref_authors={cr}"))
        except Exception as e:
            rows.append((key,'crossref',doi,'FAIL',str(e)))
        time.sleep(0.5)
    elif ax:
        p=[AX[ax.group(1)]] if ax.group(1) in AX else []
        if p:
            ar=[norm(n.split()[-1]) for n in p[0]['authors']]
            miss=[f for f in fams if f not in ar]
            rows.append((key,'arxiv',ax.group(1),'OK' if not miss else 'CHECK',f"title='{p[0]['title'][:60]}' miss={miss} journal_ref='{p[0]['journal']}'"))
        else: rows.append((key,'arxiv',ax.group(1),'FAIL',''))
    else:
        url=re.search(r'\\url\{([^}]+)\}', hp)
        rows.append((key,'url',url.group(1) if url else '-', 'URL' if url else 'NOID',''))
for r in rows: print(' | '.join(r))
print('TOTAL',len(rows),'CHECK/FAIL:',sum(r[3] in('CHECK','FAIL') for r in rows))
