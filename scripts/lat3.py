import json,os,time,socket,urllib.request as U
_ga=socket.getaddrinfo
def v4(*a,**k):
    r=_ga(*a,**k); f=[x for x in r if x[0]==socket.AF_INET]; return f or r
socket.getaddrinfo=v4
from lat import STATE,PROMPT,RESULTS
Z="https://api.z.ai/api/paas/v4/chat/completions"
def stream_probe(model,key,maxtok=200,think=False,label=""):
    body={"model":model,"max_tokens":maxtok,"temperature":0,"stream":True,
          "messages":[{"role":"system","content":PROMPT},{"role":"user","content":STATE}]}
    if not think: body["thinking"]={"type":"disabled"}
    req=U.Request(Z,data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Authorization":"Bearer "+key,"Accept":"text/event-stream"})
    t0=time.perf_counter(); ttfb=None; toks=0; buf=""; firsttok=None
    try:
        with U.urlopen(req,timeout=90) as r:
            while True:
                ln=r.readline()
                if not ln: break
                if ttfb is None: ttfb=time.perf_counter()-t0
                s=ln.decode("utf-8","ignore").strip()
                if s.startswith("data:"):
                    p=s[5:].strip()
                    if p=="[DONE]": break
                    try:
                        d=json.loads(p); ch=d.get("choices",[{}])[0]
                        piece=(ch.get("delta") or {}).get("content") or ""
                        if piece:
                            if firsttok is None: firsttok=time.perf_counter()-t0
                            toks+=len(piece); buf+=piece
                        if len(buf)>90: break            # 早停：决策 JSON 已够
                    except Exception: pass
        t1=time.perf_counter()
        print(f"{model[:26]:27}{label:10} TTFB {1000*ttfb:6.0f}ms  首token {1000*(firsttok or 0):6.0f}ms  "
              f"到齐 {1000*(t1-t0):6.0f}ms  字符{toks:4}  →tok/s≈{(toks/4)/max(t1-(firsttok or t1),.001):6.1f}  | {buf[:80].strip()}")
        return {"model":model,"ttfb_ms":round(1000*ttfb,1),"first_tok_ms":round(1000*(firsttok or 0),1),
                "total_ms":round(1000*(t1-t0),1),"chars":toks,"head":buf[:120]}
    except Exception as e:
        print(f"{model[:26]:27}{label:10}❌ {type(e).__name__} {str(e)[:60]}"); return None
if __name__=="__main__":
    key=os.environ.get("ZAI_API_KEY",""); out=[]
    for m in ["glm-4.5-flash","glm-4-flash-250414","glm-4.5-air"]:
        for i in range(2):
            r=stream_probe(m,key,label=f"run{i+1}")
            out+=[r] if r else []
        time.sleep(1)
    with (RESULTS / "lat_stream.json").open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
