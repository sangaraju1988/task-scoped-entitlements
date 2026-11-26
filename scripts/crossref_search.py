import sys, json, urllib.request, urllib.parse, time
H={'User-Agent':'tse-research-script/0.1'}
def q(text, n=3):
    url='https://api.crossref.org/works?'+urllib.parse.urlencode({'query.bibliographic':text,'rows':n,'select':'DOI,title,author,container-title,issued,type,page,volume,issue,publisher,event'})
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=60))['message']['items']
for line in sys.argv[1:]:
    print('###',line)
    for it in q(line):
        a=', '.join((x.get('family','') ) for x in it.get('author',[])[:4])
        y=(it.get('issued',{}).get('date-parts') or [[None]])[0][0]
        print(f"  {it['DOI']} | {y} | {(it.get('title') or [''])[0][:110]} | {a} | {(it.get('container-title') or [''])[0][:70]} | vol={it.get('volume')} pp={it.get('page')}")
    time.sleep(1)
