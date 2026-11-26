import sys, urllib.request, urllib.parse, xml.etree.ElementTree as ET, json, time
NS={'a':'http://www.w3.org/2005/Atom','arxiv':'http://arxiv.org/schemas/atom'}
def by_ids(ids):
    url='https://export.arxiv.org/api/query?id_list='+','.join(ids)+'&max_results=%d'%len(ids)
    return parse(urllib.request.urlopen(url,timeout=60).read())
def search(q,n=10):
    url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':q,'max_results':n,'sortBy':'relevance'})
    return parse(urllib.request.urlopen(url,timeout=60).read())
def parse(x):
    r=ET.fromstring(x);out=[]
    for e in r.findall('a:entry',NS):
        g=lambda t:(e.find(t,NS).text or '').strip().replace('\n',' ') if e.find(t,NS) is not None else ''
        out.append(dict(id=g('a:id').split('/abs/')[-1],title=' '.join(g('a:title').split()),
          authors=[a.find('a:name',NS).text for a in e.findall('a:author',NS)],
          published=g('a:published')[:10],doi=g('arxiv:doi'),journal=g('arxiv:journal_ref'),
          summary=' '.join(g('a:summary').split())[:3000]))
    return out
if __name__=='__main__':
    if sys.argv[1]=='ids': print(json.dumps(by_ids(sys.argv[2:]),indent=1))
    else:
        for q in sys.argv[2:]:
            print('### QUERY:',q)
            for p in search(q,int(12)): print(f"- {p['id']} | {p['published']} | {p['title']} | {', '.join(p['authors'][:3])}")
            time.sleep(3)
