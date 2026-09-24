from pathlib import Path

from w4 import raw

ROOT = Path(__file__).resolve().parent.parent
DUMPS = ROOT / "sources" / "forever_dumps"
BASE="https://raw.githubusercontent.com/Ketho/wow-ui-source-forever/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/"
def getdoc(f):
    return raw(BASE+f, retries=2, timeout=45)
def apis(t):
    """parse dump entries: return list of (name, kind, flags, doc, args, returns)"""
    out=[]
    for m in re.finditer(r'Name = "([A-Za-z0-9_.]+)",\s*\n\s*Type = "(Function|Variable|Event)",(.*?)\n\t\t\},', t, re.S):
        name,kind,body=m.group(1),m.group(2),m.group(3)
        flags=re.findall(r'(Secret\w+|Addon\w*Restricted\w*|AllowedWhenUntainted|ForceTaint\w*|NeverSecret|AlwaysSecret|Hardware\w*|NoInstance|Combat\w*|MayReturnNothing|Constant\w*)',body)
        doc=re.findall(r'Documentation = \{ ?"([^"]{0,220})"',body)
        args=re.findall(r'Name = "(\w+)", Type = "([^"]+)"',body)
        out.append((name,kind,sorted(set(flags)),doc,args))
    return out
import re
def report(fname, want):
    t=getdoc(fname)
    DUMPS.mkdir(parents=True, exist_ok=True)
    (DUMPS / fname).write_text(t, encoding="utf-8")
    A=apis(t)
    print(f"### {fname}  (parsed {len(A)} members, {len(t)} bytes)")
    for name,kind,flags,doc,args in A:
        if any(w.lower() in name.lower() for w in want):
            print(f"  {name} [{kind}] flags={flags}")
            for d in doc[:1]: print(f"      doc: {d}")
    return t
