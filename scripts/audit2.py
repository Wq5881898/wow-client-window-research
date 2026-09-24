from pathlib import Path

from w4 import raw
import re
B="https://raw.githubusercontent.com/Ketho/wow-ui-source-forever/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/"
ROOT = Path(__file__).resolve().parent.parent
DUMPS = ROOT / "sources" / "forever_dumps"
DUMPS.mkdir(parents=True, exist_ok=True)
SECRET_FIELDS=["SecretReturns","SecretArguments","PredicatedSecrets","Predicated","Guarded","SecretWhen","SecretOn","NeverSecret","AlwaysSecret","AddonRestricted","Restricted"]
def fetch(f):
    p=DUMPS / f
    if p.exists(): return p.read_text(encoding="utf-8")
    t=raw(B+f,retries=2,timeout=50); p.write_text(t,encoding="utf-8"); return t
def members(t):
    out=[]
    for m in re.finditer(r'\{\s*\n\s*Name = "([A-Za-z0-9_]+)",\s*\n\s*Type = "(Function|Variable|Event|Macro|Enum)",(.*?)\n\t\t\},', t, re.S):
        name,kind,body=m.group(1),m.group(2),m.group(3)
        fl={k:len(body.split(k))-1 for k in SECRET_FIELDS if k in body}
        out.append((name,kind,fl,body))
    return out
def scan(f, want, maxshow=14):
    t=fetch(f); M=members(t)
    hit=[x for x in M if any(w.lower() in x[0].lower() for w in want)] if want else M
    print(f"\n=== {f}: {len(t)}B, parsed {len(M)} members, 命中 {len(hit)}")
    for name,kind,fl,body in hit[:maxshow]:
        d=re.findall(r'Documentation = \{ "([^"]{5,150})',body)
        print(f"  {name} [{kind}] {fl if fl else ''}")
        if d: print(f"      {d[0]}")
    return t,M
