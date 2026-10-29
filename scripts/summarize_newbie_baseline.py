"""Verify the dedicated level-one character's persisted baseline."""
import hashlib
import json
import re
from pathlib import Path

from summarize_target_scenarios import ROOT, scalar_fields

source = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01\AzerothCore\Probehuman\SavedVariables\WowProbeWotLK.lua')
raw = source.read_bytes()
text = raw.decode('utf-8-sig').replace('\r\n', '\n')
block = re.split(r'^\t{2}\{\n', text, flags=re.M)[-1]
match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
meta = scalar_fields(match.group(1), 4)
records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
selected = {r['probe_id']: r for r in records if r.get('probe_id') in (
    'G4.name.player', 'G4.level.player', 'G4.health.player', 'G4.healthmax.player',
    'G4.combat.player', 'G4.name.target', 'G3.zone', 'G3.subzone')}
assert selected['G4.name.player']['value'] == 'Probehuman'
assert selected['G4.level.player']['value'] == 1
assert meta['race'] == 'Human' and meta['class'] == 'Mage'
assert selected['G4.health.player']['value'] == selected['G4.healthmax.player']['value']
result = {'source': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(),
          'meta': meta, 'observations': selected,
          'gm_mode': 'OFF, confirmed by screenshot newbie-gm-state.png; account retains GM permission',
          'test_site': 'Northshire Abbey spawn lawn; visually gentle ground near friendly Deputy Willem; not a surveyed flat plane'}
output = ROOT / 'results' / 'newbie_baseline_2026-10-21.json'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
