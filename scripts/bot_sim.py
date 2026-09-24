# -*- coding: utf-8 -*-
"""合成场景仿真台 v4：本地状态机 + L2 云端委托 + 故障注入 + 配额/退避/熔断。纯标准库。
跑法：`python scripts/bot_sim.py` → 终端表 + `results/sim_result.json`

这是用于暴露契约和状态机缺陷的离线仪器，不预测真机产能或安全性。
v4 修正两项比较完整性问题：云路径不再读取隐藏逃生方向；naive 路径不再经过 validate_decision。
v1→v3 曾暴露逐字节哈希、429 退避、脱困计数和答案类型四类设计问题。
"""
import json, math, random, statistics as st
from pathlib import Path

from bot_contract import (Snap, MELEE, validate_decision, Breaker, cost_per_call, TOK_IN, TOK_OUT)

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
TICK, GCD = 0.1, 1.5
SP_RANGE = {"Chop":8.0,"Rend":9.0,"Shoot":25.0}
SP_DMG   = {"Chop":14.0,"Rend":20.0,"Shoot":9.0}
RATES = {"ok":{}, "timeout":{"timeout":1.0}, "ratelimit":{"ratelimit":1.0}, "empty":{"empty":1.0},
         "nonjson":{"nonjson":1.0}, "halluc":{"halluc":1.0},
         "mixed":{"timeout":.15,"ratelimit":.15,"empty":.10,"nonjson":.10,"halluc":.20}}
HALLUC = ["CAST:Invisibility","CAST:Shadowforging","FACEHUG","MOVE:UP","CAST:Chop","RETREAT"]
QUOTA_PER_H = 4          # 设计上限：L2 委托 ≤4 次/小时

class World:
    SPEED, MOBDPS = 0.4, 0.004          # 4 单位/s；每怪 0.04 血/s
    def __init__(self, seed, scen):
        self.rng=random.Random(seed); self.t=0.0
        self.px=self.py=0.0; self.hp=self.mana=1.0
        self.combat=False; self.gcd=self.potion_cd=0.0
        self.mobs=[]; self.dead=0; self.node=None; self.bags_free=18
        self.stuck_until=0.0; self.escape_dir=None
        self.kills=self.gathers=self.deaths=0
        self.stuck_ticks=self.loss_ticks=self.wasted=self.stuck_eps=0
        self.esc_local=self.esc_cloud=0
        self.cloud_actions=set()        # 云端曾给过的动作（用于脱困归因）
        self.scen=scen
    def spawn(self):
        r=self.rng
        if len(self.mobs)<4 and r.random()<.08:
            self.mobs.append([r.uniform(-24,24),r.uniform(-24,24),r.uniform(28,45)])
        if self.node is None and r.random()<.05:
            self.node=[self.px+r.uniform(3,18),self.py+r.uniform(3,18)]
        if self.scen in("stuck","mixed") and self.t>self.stuck_until and r.random()<.004:
            self.stuck_until=self.t+r.uniform(6,14); self.stuck_eps+=1
            self.escape_dir=r.choice(["N","E","S","W"])       # 隐藏的"正确脱困方向"
        if self.scen in("add","mixed") and r.random()<.004:
            self.mobs.append([self.px+r.uniform(1,6),self.py+r.uniform(1,6),45.0])
    def d(self,m): return math.hypot(self.px-m[0],self.py-m[1])
    def snap(self):
        tg=min(self.mobs,key=self.d) if self.mobs else None
        dist=self.d(tg) if tg else 99.0
        vision=min(1.0,max(0.0,self.hp+self.rng.gauss(0,.04)))    # A 档不可读 → 血条像素比例
        tdir=None
        if tg:
            dx,dy=tg[0]-self.px,tg[1]-self.py
            tdir=("E" if dx>0 else "W") if abs(dx)>abs(dy) else ("N" if dy>0 else "S")
        return Snap(map="Zephras",x=round(self.px,1),y=round(self.py,1),combat=self.combat,
            target=("Rotgill" if tg else None),texists=bool(tg),tdist=round(dist,1),tdir=tdir,cast="none",
            hpr=round(vision,2),powerr=round(self.mana,2),bags_free=self.bags_free,
            cd={k:round(max(0,self.gcd if k!="Shoot" else 0),1) for k in ("Chop","Rend","Shoot")},
            potionReady=self.potion_cd<=0,stuck=self.t<self.stuck_until,lootable=self.dead>0,
            nodeInRange=bool(self.node and math.hypot(self.px-self.node[0],self.py-self.node[1])<=5))
    def step(self,action):
        self.t+=TICK; self.gcd=max(0,self.gcd-TICK); self.potion_cd=max(0,self.potion_cd-TICK)
        self.spawn()
        stuck_now=self.t<self.stuck_until
        if stuck_now:
            self.stuck_ticks+=1
            if action and action.startswith("MOVE") and action[5:]==self.escape_dir:
                if action in self.cloud_actions: self.esc_cloud+=1
                else: self.esc_local+=1
                self.stuck_until=self.t                        # 方向对了 → 立即脱困
        if action and action.startswith("MOVE") and self.t>=self.stuck_until:
            dx,dy={"N":(0,self.SPEED),"E":(self.SPEED,0),"S":(0,-self.SPEED),"W":(-self.SPEED,0)}.get(action[5:],(0,0))
            self.px+=dx; self.py+=dy
        if action=="ATTACK" and self.mobs and min(map(self.d,self.mobs))<=MELEE: self.combat=True
        if action and action.startswith("CAST:") and self.gcd<=0 and self.mobs:
            m=min(self.mobs,key=self.d)
            if self.d(m)<=SP_RANGE.get(action[5:],20.0):
                m[2]-=SP_DMG.get(action[5:],10.0); self.gcd=GCD; self.combat=True
                if m[2]<=0: self.mobs.remove(m); self.dead+=1; self.kills+=1
        if action=="LOOT" and self.dead:
            self.dead-=1; self.bags_free-=1
            self.combat=bool(self.mobs and min(map(self.d,self.mobs))<=10)
        if action=="INTERACT" and self.node and math.hypot(self.px-self.node[0],self.py-self.node[1])<=5:
            self.node=None; self.gathers+=1; self.bags_free-=1
        if action=="RETREAT":
            self.px-=3 if self.px>0 else -3; self.py+=2
            if not self.mobs or min(map(self.d,self.mobs))>18: self.combat=False; self.hp=min(1,self.hp+.006)
        if action=="POTION" and self.potion_cd<=0: self.hp=min(1,self.hp+.35); self.potion_cd=60
        if action=="BAG_FULL": self.bags_free=18
        if action in("NONE",None): self.loss_ticks+=1
        if action=="WASTED": self.wasted+=1; self.gcd=GCD
        near=[m for m in self.mobs if self.d(m)<=8]
        if self.combat and near: self.hp-=self.MOBDPS*len(near)
        if self.hp<=0:
            self.deaths+=1; self.hp=1.0; self.mobs.clear(); self.dead=0; self.px=self.py=0.0

def local_policy(s):
    """L0/L1 consumes only the synthetic snapshot; None means request L2."""
    if s.combat and (s.hpr or 1)<.30: return "POTION" if (s.hpr or 0)<.40 and s.potionReady else "RETREAT"
    if s.bags_free<=0: return "BAG_FULL"
    if s.lootable: return "LOOT"
    if s.nodeInRange: return "INTERACT"
    if s.stuck: return None                                     # 卡住 → 上升一层
    if not s.texists: return "MOVE:N"
    if s.tdist<=MELEE:
        for sp in ("Rend","Chop"):
            if s.cd.get(sp,9)<=0: return "CAST:"+sp
        return "ATTACK"
    return "MOVE:"+(s.tdir or "N")

class Cloud:
    """在线 agent 端点模型：往返 6–25 s（实测）+ 每小时配额 + 7 种故障"""
    def __init__(self,rng,fault="ok",hard=45.0,quota=QUOTA_PER_H,hours=1.0):
        self.rng=rng; self.fault=fault; self.hard=hard; self.calls=0
        self.pend=[]; self.backoff_until=0.0; self.last_answer=None
        self.quota=max(1,int(quota*hours))
        self.stats=dict.fromkeys(("issued","accepted","quota","ratelimit","timeout","empty","nonjson",
                                  "halluc","rejected","stale","blocked"),0)
    def askable(self,now): return now>=self.backoff_until and self.stats["issued"]<self.quota
    def ask(self,snap,now,kind="generic",blocking=False):
        r=self.rng
        if self.stats["issued"]>=self.quota:
            self.stats["quota"]+=1; return "quota"
        self.calls+=1; self.stats["issued"]+=1
        lat=r.uniform(6,25)
        pick=next((k for k,p in RATES[self.fault].items() if r.random()<p),None)
        if pick=="ratelimit":
            self.stats["ratelimit"]+=1; self.backoff_until=now+120; return "ratelimit"
        if pick=="empty":   payload=None
        elif pick=="nonjson": payload="Sorry! I need more context to decide."
        elif pick=="halluc":  payload={"action":r.choice(HALLUC),"confidence":.8}
        elif kind=="stuck":
            payload={"action":"MOVE:"+r.choice(("N","E","S","W")),"confidence":.5}
        else: payload={"action":"CAST:Chop","confidence":.9}
        if pick=="timeout": lat=self.hard
        if blocking: self.stats["blocked"]+=1
        self.pend.append((now+lat,pick,payload,snap.relevance_hash()))
        return "sent"
    def poll(self,now):
        for i,(due,pick,payload,rh) in enumerate(self.pend):
            if now<due: continue
            self.pend.pop(i)
            if pick=="timeout": self.stats["timeout"]+=1; return None
            return (payload,rh,pick)
        return None

def run(scen,policy,fault,dur=1800,seed=7,quota=QUOTA_PER_H):
    w=World(seed,scen); rng=random.Random(seed*31+1)
    cloud=Cloud(rng,fault,quota=max(1,int(quota*dur/3600)))
    brk=Breaker(); wait_until=0.0; rej={}; asked_ep=-1
    for _ in range(int(dur/TICK)):
        s=w.snap(); now=w.t
        if now<wait_until: w.step("NONE"); continue             # 天真策略：整循环阻塞等云端
        got=cloud.poll(now); act=None
        if got:
            payload,rh,pick=got
            if payload is None:
                brk.record(True,now); rej[pick or "empty"]=rej.get(pick or "empty",0)+1
            else:
                if policy=="naive":
                    a=payload.get("action") if isinstance(payload,dict) else payload
                    act=a
                    cloud.stats["accepted"]+=1
                    cloud.last_answer=a
                    if isinstance(a,str): w.cloud_actions.add(a)
                else:
                    ok,a,why=validate_decision(payload,s,rh,s.relevance_hash(),SP_RANGE)
                    if ok:
                        brk.record(False,now); cloud.stats["accepted"]+=1; act=a
                        cloud.last_answer=a; w.cloud_actions.add(a)
                    elif why=="陈旧决策(状态已变)":
                        brk.record(True,now); cloud.stats["stale"]+=1; rej["陈旧"]=rej.get("陈旧",0)+1
                    else:
                        brk.record(True,now); cloud.stats["rejected"]+=1; rej[why]=rej.get(why,0)+1
        if act is None:
            if policy=="naive" and s.stuck:
                stt=cloud.ask(s,now,kind="stuck",blocking=True)
                if stt=="sent": wait_until=cloud.pend[-1][0]
                w.step("NONE"); continue
            lp=local_policy(s)
            if lp is None:                                      # 卡住：先局部微脱困（4 方向轮试）
                if w.stuck_ticks<25: lp=["MOVE:N","MOVE:E","MOVE:S","MOVE:W"][(w.stuck_ticks//6)%4]
                elif policy!="local_only" and brk.allow(now) and cloud.askable(now) and asked_ep!=w.stuck_eps:
                    cloud.ask(s,now,kind="stuck"); asked_ep=w.stuck_eps
                    lp="RETREAT" if s.combat else "MOVE:S"
                else: lp="RETREAT" if s.combat else "NONE"      # 配额耗尽 → 守势等待
            act=lp
        w.step(act)
    h=dur/3600.0; c=cloud.stats
    return dict(scen=scen,policy=policy,fault=fault,kills=round(w.kills/h,1),gathers=round(w.gathers/h,1),
        deaths=w.deaths,stuck_pct=round(100*w.stuck_ticks/(dur/TICK),2),loss_pct=round(100*w.loss_ticks/(dur/TICK),2),
        wasted=w.wasted,episodes=w.stuck_eps,esc_local=w.esc_local,esc_cloud=w.esc_cloud,
        avg_stuck_s=round(w.stuck_ticks/max(1,w.stuck_eps)*TICK,1),
        issued=c["issued"],accepted=c["accepted"],quota_denied=c["quota"],blocked=c["blocked"],
        ratelimit=c["ratelimit"],timeout=c["timeout"],rejected=c["rejected"],stale=c["stale"],
        breaker=brk.trips,calls_h=round(cloud.calls/h,1),cost_h=round(cloud.calls/h*cost_per_call(),6),rej=rej)

if __name__=="__main__":
    scen_fault=[("calm","ok"),("stuck","ok"),("add","ok"),("mixed","mixed"),
                ("mixed","ratelimit"),("mixed","halluc")]
    SEEDS=range(12); rows=[]
    for scen,f in scen_fault:
        for p in ("local_only","cloud_validated","naive"):
            rs=[run(scen,p,f,seed=100+k) for k in SEEDS]
            M=lambda k: round(st.mean(r[k] for r in rs),2)
            rej={}
            for r in rs:
                for k,v in r["rej"].items(): rej[k]=rej.get(k,0)+v
            rows.append(dict(scen=scen,fault=f,policy=p,kills=M("kills"),gathers=M("gathers"),
                deaths=M("deaths"),stuck_pct=M("stuck_pct"),loss_pct=M("loss_pct"),wasted=M("wasted"),
                episodes=M("episodes"),esc_local=M("esc_local"),esc_cloud=M("esc_cloud"),avg_stuck_s=M("avg_stuck_s"),
                issued=M("issued"),accepted=M("accepted"),quota_denied=M("quota_denied"),blocked=M("blocked"),
                ratelimit=M("ratelimit"),timeout=M("timeout"),rejected=M("rejected"),stale=M("stale"),
                breaker=M("breaker"),calls_h=M("calls_h"),cost_h=M("cost_h"),
                rej={k:round(v/len(rs),1) for k,v in sorted(rej.items(),key=lambda x:-x[1])}))
    with (RESULTS / "sim_result.json").open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    hdr=(f"{'场景':6}{'故障':10}{'策略':16}{'击杀/h':>7}{'死亡':>5}{'卡住%':>7}{'卡住次':>6}{'均卡s':>6}"
         f"{'本地解困':>7}{'云端解困':>7}{'委托':>5}{'采纳':>5}{'配额拒':>7}{'限流':>5}{'超时':>5}{'拒校验':>6}{'熔断':>5}{'$/h':>8}")
    print(hdr); print("-"*150)
    for r in rows:
        print(f"{r['scen']:6}{r['fault']:10}{r['policy']:16}{r['kills']:7.1f}{r['deaths']:5.2f}"
              f"{r['stuck_pct']:7.2f}{r['episodes']:6.1f}{r['avg_stuck_s']:6.1f}"
              f"{r['esc_local']:7.1f}{r['esc_cloud']:7.1f}{r['issued']:5.1f}{r['accepted']:5.1f}"
              f"{r['quota_denied']:7.0f}{r['ratelimit']:5.1f}{r['timeout']:5.1f}{r['rejected']:6.1f}"
              f"{r['breaker']:5.1f}{r['cost_h']:8.5f}")
    print("\n校验拒绝原因分布（次/30min，cloud_validated 组）:")
    for r in rows:
        if r["policy"]!="cloud_validated": continue
        print(f"  {r['scen']:6}{r['fault']:10}{r['rej']}")
    print("\n快照字节数:",World(1,"calm").snap().byte_len(),"B | 单次调用成本 $",round(cost_per_call(),6),
          f"(入{TOK_IN}/出{TOK_OUT} tok @ $0.60/$2.40 per M)")
