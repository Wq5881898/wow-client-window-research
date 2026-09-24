import re,html,os,time,json,urllib.request,urllib.parse,hashlib
from pathlib import Path

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ROOT = Path(__file__).resolve().parent.parent
C = ROOT / ".cache" / "web"
C.mkdir(parents=True, exist_ok=True)
def raw(u,ua=UA,retries=3,timeout=35,nocache=False):
    k=C / (hashlib.md5((u+(ua or "")).encode()).hexdigest()+".txt")
    if k.exists() and not nocache: return k.read_text(encoding="utf-8")
    last=None
    for i in range(retries):
        try:
            req=urllib.request.Request(u,headers={"User-Agent":ua or UA,"Accept-Language":"en-US,en;q=0.9"})
            d=urllib.request.urlopen(req,timeout=timeout).read().decode('utf-8','ignore')
            k.write_text(d,encoding="utf-8"); return d
        except Exception as e: last=e; time.sleep(1.2+1.2*i)
    raise last
def _jin(u,h=None):
    hh={"User-Agent":"Mozilla/5.0"}; hh.update(h or {})
    return urllib.request.urlopen(urllib.request.Request("https://r.jina.ai/"+u,headers=hh),timeout=50).read().decode('utf-8','ignore')
def wiki(q,n=6):
    u="https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch="+urllib.parse.quote(q)+"&format=json&srlimit="+str(n)
    return [(x['title'],html.unescape(re.sub('<.*?>','',x['snippet']))) for x in json.loads(raw(u,"research/1.0"))['query']['search']]
def wtext(t):
    u="https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&redirects=1&titles="+urllib.parse.quote(t)
    return list(json.loads(raw(u,"research/1.0"))['query']['pages'].values())[0].get('extract','')
def gh(q,n=6,sort="stars"):
    u="https://api.github.com/search/repositories?q="+urllib.parse.quote(q)+"&sort="+sort+"&per_page="+str(n)
    try: return [(i['full_name'],i['stargazers_count'],(i.get('description') or '')[:115],i['pushed_at'][:10]) for i in json.loads(raw(u,"x"))['items']]
    except Exception as e: return [("ERR "+str(e)[:60],0,'','')]
def gcode(q,n=8):
    u="https://api.github.com/search/code?q="+urllib.parse.quote(q)+"&per_page="+str(n)
    try:
        d=json.loads(raw(u,"x")); return d.get('total_count'),[(i['repository']['full_name'],i['path']) for i in d.get('items',[])]
    except Exception as e: return "ERR "+str(e)[:70],[]
def show(q,n=6):
    print("### GH:",q)
    for a in gh(q,n): print(f"   {a[0]} ★{a[1]} ({a[3]}) | {a[2]}")
    print()
