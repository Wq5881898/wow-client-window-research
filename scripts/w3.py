import re,html,os,time,urllib.request,urllib.parse,hashlib,json
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def raw(u,ua=UA,retries=3,timeout=30):
    last=None
    for i in range(retries):
        try:
            req=urllib.request.Request(u,headers={"User-Agent":ua,"Accept-Language":"en-US,en;q=0.9","Accept":"text/html,application/json,*/*"})
            return urllib.request.urlopen(req,timeout=timeout).read().decode('utf-8','ignore')
        except Exception as e:
            last=e; time.sleep(2+2*i)
    raise last
def jina(u,extra=None):
    h={"User-Agent":"Mozilla/5.0"}
    if extra: h.update(extra)
    return raw("https://r.jina.ai/"+u,ua=None) if False else _jin(u,h)
def _jin(u,h):
    req=urllib.request.Request("https://r.jina.ai/"+u,headers=h)
    return urllib.request.urlopen(req,timeout=45).read().decode('utf-8','ignore')
def txt(u):
    t=raw(u); t=re.sub(r'<(script|style).*?</\1>','',t,flags=re.S); t=re.sub('<[^>]+>',' ',t)
    return re.sub(r'\s+',' ',html.unescape(t))
def hits(label,text,phrases,ctx=700):
    print(f"--- {label} (len {len(text)}) ---")
    found=False
    for p in phrases:
        for m in list(re.finditer(re.escape(p.lower()),text.lower()))[:2]:
            found=True
            print(f"\n   >>> [{p}] "+" ".join(text[max(0,m.start()-250):m.start()+ctx].split()))
    if not found: print("   (no phrase hit)")
