import json
import sys

path = sys.argv[1]
d = json.load(open(path, encoding='utf-8'))
print('status', d['status'], '| reason', d.get('reason'), '| error', d.get('error'))
print('start', d.get('start'))
print('final', d.get('final'), '| button', d.get('dialog_button'))
for s in d.get('steps', []):
    det = s['detail']
    dist = det.get('distance')
    dist = ('%.5f' % dist) if isinstance(dist, float) else str(dist)
    print('  %-6s dist=%s facing=%s phase=%s %s %s' % (
        s['action'], dist, det.get('facing'), det.get('phase'),
        det.get('direction', ''), det.get('seconds', '')))
