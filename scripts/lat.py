import json,os,socket,ssl,time,urllib.request as U
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
# 强制 IPv4（排除 IPv6 路径干扰）
_ga=socket.getaddrinfo
def v4(*a,**k):
    r=_ga(*a,**k)
    f=[x for x in r if x[0]==socket.AF_INET]
    return f or r
socket.getaddrinfo=v4

STATE='{"map":"Zephras","x":41.2,"y":63.7,"combat":true,"target":"Rotgill","texists":true,"tdist":7.3,"cast":"none","hpr":0.62,"powerr":0.44,"bags":{"free":3},"cd":{"Chop":0,"Rend":1.2},"stuck":false}'
PROMPT=("You are the decision layer of a WoW bot. Given the state JSON, return ONLY minified JSON "
 "{\"action\":<one of: ATTACK,CAST:Chop,CAST:Rend,RETREAT,BAG_FULL,NONE>,\"confidence\":0-1,\"why\":\"<=12 words\"}. No prose.")
CANDS=[("QWEN_API_KEY","https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions","qwen-turbo-latest"),
       ("QWEN_API_KEY","https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions","qwen-flash"),
       ("ZAI_API_KEY","https://api.z.ai/api/paas/v4/chat/completions","glm-4.5-flash"),
       ("CHATGPT_API_KEY","https://api.openai.com/v1/chat/completions","gpt-4o-mini"),
       ("MINIMAX_API_KEY","https://api.minimax.io/v1/chat/completions","MiniMax-M2"),
       ("QWEN_API_KEY","https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions","qwen-turbo")]
def call(url,key,model,maxtok=60):
    body=json.dumps({"model":model,"messages":[{"role":"system","content":PROMPT},{"role":"user","content":STATE}],
                     "max_tokens":maxtok,"temperature":0}).encode()
    req=U.Request(url,data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
    t0=time.perf_counter()
    try:
        with U.urlopen(req,timeout=45) as r:
            t1=time.perf_counter(); raw=r.read()
        t2=time.perf_counter()
        j=json.loads(raw); u=j.get("usage") or {}
        ct=(u.get("completion_tokens") or u.get("output_tokens") or 0)
        txt=(j["choices"][0]["message"]["content"] or "")
        gen=t2-t1
        return dict(ms=1000*(t2-t0),ttfb=1000*(t1-t0),gen=1000*gen,ct=ct,tps=(ct/(gen) if gen>0 and ct else 0),ok=True,txt=txt[:110],model=model,host=url.split("/")[2])
    except Exception as e:
        return dict(ok=False,err=f"{type(e).__name__}: {str(e)[:80]}",model=model,host=url.split("/")[2],ms=1000*(time.perf_counter()-t0))
if __name__=="__main__":
    print(f"{'host':32}{'model':18}{'连接+TTFB':>10}{'生成':>8}{'总':>8}{'tok':>5}{'tok/s':>8}  结果/错误")
    good=[]
    for k,url,m in CANDS:
        key=os.environ.get(k)
        if not key: print(f"{url.split('/')[2]:32}{m:18} 无 key"); continue
        r=call(url,key,m)
        if r["ok"]:
            print(f"{r['host']:32}{r['model']:18}{r['ttfb']:10.0f}{r['gen']:8.0f}{r['ms']:8.0f}{r['ct']:5.0f}{r['tps']:8.1f}  {r['txt']}")
            good.append(r)
        else:
            print(f"{r['host']:32}{r['model']:18}{r['ms']:10.0f}{'':34} ❌ {r['err']}")
    with (RESULTS / "lat_result.json").open("w", encoding="utf-8") as f:
        json.dump(good, f, ensure_ascii=False, indent=1)
