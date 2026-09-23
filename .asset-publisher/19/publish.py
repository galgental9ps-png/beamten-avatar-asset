from pathlib import Path
from PIL import Image
import io, json, sys

root = Path('BeamtenMonitorAvatar/Assets 19')
phrase = {
    'theme': 'Apothekentag',
    'line': 'Ich gehe zurück in die Apotheke – der Feierabend ist heute ganz ohne Nebenwirkungen genehmigt.',
}

if '--write-json' in sys.argv:
    path = root / 'Sprüche/Abschiedsspruch.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(phrase, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

required = {
    'Avatar/Idle.png': (1024, 1536),
    'Avatar/Actions.png': (1536, 1024),
    'MonitorScene/MonitorScene.png': (1672, 941),
    'Klingel/MonitorBell.png': (1254, 1254),
}
for rel, size in required.items():
    data = (root / rel).read_bytes()
    image = Image.open(io.BytesIO(data))
    image.load()
    assert image.format == 'PNG' and image.mode == 'RGBA' and image.size == size, (rel, image.format, image.mode, image.size)
    assert image.getchannel('A').getextrema()[0] == 0 and image.getchannel('A').getextrema()[1] > 200, rel
    Image.open(io.BytesIO(data)).verify()

actions = Image.open(root / 'Avatar/Actions.png')
bounds = []
for index in range(8):
    x, y = (index % 4) * 384, (index // 4) * 512
    cell = actions.crop((x, y, x + 384, y + 512))
    bbox = cell.getchannel('A').getbbox()
    assert bbox
    margins = (bbox[0], bbox[1], 384 - bbox[2], 512 - bbox[3])
    assert min(margins) >= 20, (index, bbox, margins)
    bounds.append(bbox)
assert bounds[1][3] == bounds[2][3], bounds

payload = json.loads((root / 'Sprüche/Abschiedsspruch.json').read_text(encoding='utf-8'))
assert payload == phrase and set(payload) == {'theme', 'line'} and len(payload['line']) <= 180
print(json.dumps({'validated': True, 'bounds': bounds}, ensure_ascii=False))
