# -*- coding: utf-8 -*-
"""契约层：合成状态快照、动作白名单、校验器、熔断器。纯标准库。
预研阶段的一次性离线仪器，不是产品代码。所有输入分布和观测字段均为人为模型；
结果只能用于检查代码路径与契约假设，不能预测真机产能、安全性或可行性。
"""
import json, hashlib

MELEE, DEFAULT_RANGE = 5.0, 20.0
BASE_ACTIONS = {"ATTACK","TARGET_NEAREST","LOOT","INTERACT","RETREAT","BAG_FULL","POTION","NONE"}
MOVE = {"MOVE:N","MOVE:E","MOVE:S","MOVE:W"}

class Snap:
    """合成快照。`hpr`/`powerr`、`tdir` 和 `potionReady` 都是仿真假设的观测，
    不是已经证实可由 Forever 客户端稳定取得的数据。"""
    FIELDS = ("map","x","y","combat","target","texists","tdist","tdir","cast","hpr","powerr",
              "bags_free","cd","potionReady","stuck","lootable","nodeInRange")
    def __init__(self, **kw):
        for f in self.FIELDS: setattr(self, f, kw.get(f))
        self.cd = dict(kw.get("cd") or {})
    def to_json(self):
        return json.dumps({f:getattr(self,f) for f in self.FIELDS},
                          separators=(",",":"), sort_keys=True)
    def byte_len(self): return len(self.to_json().encode())
    def state_hash(self, tick=None):
        # 只对内容做哈希（不含 tick）：内容变了才算"陈旧"
        return hashlib.sha1(self.to_json().encode()).hexdigest()[:12]
    def relevance_hash(self):
        """只哈希**与决策相关**的字段（分桶）。
        ⚠ 仿真台第一轮测出来的坑：坐标每 tick 都在变，若用逐字节哈希→**所有**委托决策皆被判陈旧（丢弃率 100%）。
        所以下行距离/血量分桶，只保留“就绪/不就绪”、“在/不在”这类语义。"""
        return hashlib.sha1(json.dumps({
            "tgt": self.target, "ex": self.texists, "d": round((self.tdist or 0)/2)*2,
            "dir": self.tdir, "cb": bool(self.combat), "h": round((self.hpr or 0)/.1), "st": bool(self.stuck),
            "pot": bool(self.potionReady),
            "loot": bool(self.lootable), "node": bool(self.nodeInRange), "bag": (self.bags_free or 0)//4,
            "cd": {k: (1 if (v or 0) > 0 else 0) for k, v in sorted((self.cd or {}).items())},
        }, sort_keys=True, separators=(",",":")).encode()).hexdigest()[:12]

def spell_actions(snap): return {"CAST:"+k for k in snap.cd} | {"CAST:"+k for k in ("Chop","Rend","Shoot")}

def validate_decision(payload, snap, sent_hash, cur_hash, ranges=None):
    """三重校验：①格式/白名单 ②技能存在且 CD 就绪且射程够 ③陈旧即丢弃。
    返回 (ok, action, reason)"""
    ranges = ranges or {}
    if not isinstance(payload, dict):
        return False, None, "非JSON/非对象"
    a = payload.get("action")
    if not isinstance(a, str):
        return False, None, "action字段缺/类型错"
    if a not in (BASE_ACTIONS | MOVE | spell_actions(snap)):
        return False, None, "白名单外动作"
    if cur_hash != sent_hash:
        return False, None, "陈旧决策(状态已变)"
    if a == "ATTACK" and (not snap.texists or snap.tdist > MELEE):
        return False, None, "ATTACK距离不可行"
    if a.startswith("CAST:"):
        sp = a[5:]
        if sp not in snap.cd:            return False, None, "技能不在已知表(疑似幻觉)"
        if snap.cd.get(sp, 0) > 0:       return False, None, "CD未就绪"
        if not snap.texists:             return False, None, "无目标却施法"
        if snap.tdist > ranges.get(sp, DEFAULT_RANGE): return False, None, "超出射程"
    if a == "INTERACT" and not snap.nodeInRange: return False, None, "采集点不在范围内"
    if a == "LOOT" and not snap.lootable:        return False, None, "无可拾取物"
    return True, a, "ok"

class Breaker:
    """连续 3 次失败 → 熔断 open_s 秒（保守模式：只用本地策略）"""
    def __init__(self, threshold=3, open_s=600):
        self.fails = 0; self.open_until = -1; self.trips = 0
        self.threshold, self.open_s = threshold, open_s
    def allow(self, now_s):
        return now_s >= self.open_until
    def record(self, failed, now_s):
        if not failed:
            self.fails = 0; return
        self.fails += 1
        if self.fails >= self.threshold:
            self.trips += 1; self.open_until = now_s + self.open_s; self.fails = 0

# —— 成本模型（实测：入 ~130 token，出 ~26 token）——
TOK_IN, TOK_OUT = 130, 26
def cost_per_call(price_in_per_M=0.60, price_out_per_M=2.40):
    return TOK_IN*price_in_per_M/1e6 + TOK_OUT*price_out_per_M/1e6
