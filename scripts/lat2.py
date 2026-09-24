import json,os,time,urllib.request as U,socket
_ga=socket.getaddrinfo
def v4(*a,**k):
    r=_ga(*a,**k); f=[x for x in r if x[0]==socket.AF_INET]; return f or r
socket.getaddrinfo=v4
from lat import STATE,PROMPT,RESULTS
def call(url,key,model,maxtok=60,extra=None,label=""):
    body={"model":model,"max_tokens":maxtok,"temperature":0,
          "messages":[{"role":"system","content":PROMPT},{"role":"user","content":STATE}]}
    if extra: body.update(extra)
    req=U.Request(url,data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
    t0=time.perf_counter()
    try:
        with U.urlopen(req,timeout=90) as r:
            t1=time.perf_counter(); raw=r.read()
        t2=time.perf_counter(); j=json.loads(raw); u=j.get("usage") or {}
        ct=u.get("completion_tokens") or u.get("output_tokens") or 0
        rt=u.get("completion_tokens_details",{}) or {}
        txt=(j["choices"][0]["message"].get("content") or "")[:120]
        gen=t2-t1
        print(f"{label:12}{model[:30]:31}连接+TTFB {1000*(t1-t0):6.0f} 生成 {1000*gen:6.0f} 总 {1000*(t2-t0):6.0f}ms "
              f"tok={ct} think={rt.get('reasoning_tokens','-')} tok/s={(ct/gen if gen>0 else 0):6.1f} | {txt}")
        return {"model":model,"total_ms":round(1000*(t2-t0),1),"ttfb_ms":round(1000*(t1-t0),1),
                "gen_ms":round(1000*gen,1),"completion_tokens":ct,"usage":u,"txt":txt,"label":label}
    except Exception as e:
        print(f"{label:12}{model[:30]:31}❌ {type(e).__name__} {str(e)[:70]}")
        return None
if __name__=="__main__":
    OR="https://openrouter.ai/api/v1/chat/completions"; Z="https://api.z.ai/api/paas/v4/chat/completions"
    out=[]
    for k in ["QWEN_API_KEY","CHATGPT_API_KEY","MINIMAX_API_KEY","ZAI_API_KEY"]:
        key=os.environ.get(k,"")
        if not key: continue
        r=call(OR,key,"ARC4NUM/Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit",60,label=k[:5])
        out+=[r] if r else []
        if r: break
    # 关掉思考再试 ZAI
    for m in ["glm-4.5-flash","glm-4.5-air"]:
        r=call(Z,os.environ.get("ZAI_API_KEY",""),m,60,extra={"thinking":{"type":"disabled"}},label="ZAI-nothink")
        out+=[r] if r else []
    r=call(Z,os.environ.get("ZAI_API_KEY",""),"glm-4-flash-air-250414",60,label="ZAI-air")
    out+=[r] if r else []
    with (RESULTS / "lat_result2.json").open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
