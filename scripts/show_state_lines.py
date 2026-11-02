import ast
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding='utf-8', errors='replace')
keys = ('target_guid', 'target_exists', 'target_attackable', 'target_health',
        'target_class_name', 'chat_open', 'sequence', 'health', 'combat',
        'spell_range', 'corpse_exists', 'pos_x', 'pos_y')
for line in text.splitlines():
    line = line.strip()
    if not line.startswith(('{', '[')):
        print(line[:160])
        continue
    start = line.find('{')
    if start < 0:
        continue
    try:
        state = ast.literal_eval(line[start:])
    except Exception:
        print('unparsed:', line[:120])
        continue
    if not isinstance(state, dict):
        print(line[:160])
        continue
    print({k: state.get(k) for k in keys})
