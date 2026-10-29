"""Session-2: enumerate nearby objects (3.3.5a client API) to find a real NPC."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5

LUA = (
    'local f=_G.WowLabNear '
    'if not f then '
    'f=CreateFrame(\"Frame\") _G.WowLabNear=f f.n=0 f.out={} '
    'f:SetScript(\"OnUpdate\", function(s) '
    's.n=s.n+1 '
    'if s.n>25 then return end '
    'SetBaseCursorByName(\"ATTACK\") '
    'local g=GetCursorObject() '
    'if g then local ok,name=pcall(GetName, g) if ok and name then s.out[#s.out+1]=name end end '
    'SetBaseCursorByName(\"POINT\") '
    'MoveCursor(200+s.n*20, 380) '
    'if s.n==25 then UIErrorsFrame:AddMessage(\"OBJ=\"..table.concat(s.out,\",\"), 0, 1, 0, 1, 8) end '
    'end) '
    'end '
    'UIErrorsFrame:AddMessage(\"NEARSCAN_ON\", 0, 1, 0, 1, 5)'
)


def main():
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    import subprocess
    subprocess.run([
        'C:\\APP\\Python\\python.exe',
        str(ROOT / 'scripts' / 'lab_run.py'), LUA,
    ])
    return 0


if __name__ == '__main__':
    sys.exit(main())
