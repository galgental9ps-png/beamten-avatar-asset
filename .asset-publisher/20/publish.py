import base64
import io
import json
import os
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SET = ROOT / 'BeamtenMonitorAvatar/Assets 20'
PARTS = ROOT / '.asset-publisher/20'
FILES = {
    'Avatar/Idle.png': ('idle', (1024, 1536)),
    'Avatar/Actions.png': ('actions', (1536, 1024)),
    'MonitorScene/MonitorScene.png': ('scene', (1672, 941)),
    'Klingel/MonitorBell.png': ('bell', (1254, 1254)),
}


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def materialize():
    for rel, (key, _) in FILES.items():
        chunks = sorted((PARTS / key).glob('part-*'))
        assert chunks, key
        data = base64.b64decode(''.join(p.read_text(encoding='ascii') for p in chunks), validate=True)
        path = SET / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, path)
    phrase_path = SET / 'Sprüche/Abschiedsspruch.json'
    phrase_path.parent.mkdir(parents=True, exist_ok=True)
    phrase_path.write_text(
        '{"theme":"Museumstag","line":"Ich gehe zurück ins Museum – der Feierabend bekommt heute seinen ordnungsgemäßen Ehrenplatz."}',
        encoding='utf-8',
    )


def validate():
    verified = []
    for rel, (_, size) in FILES.items():
        path = SET / rel
        data = path.read_bytes()
        assert data and data.startswith(b'\x89PNG\r\n\x1a\n')
        image = Image.open(io.BytesIO(data))
        image.load()
        assert image.format == 'PNG' and image.mode == 'RGBA' and image.size == size
        Image.open(io.BytesIO(data)).verify()
        assert image.getchannel('A').getextrema()[0] == 0
        if rel == 'Avatar/Actions.png':
            bounds = []
            for index in range(8):
                x, y = index % 4 * 384, index // 4 * 512
                bbox = image.crop((x, y, x + 384, y + 512)).getchannel('A').getbbox()
                assert bbox
                margins = (bbox[0], bbox[1], 384 - bbox[2], 512 - bbox[3])
                assert min(margins) >= 20, (index, margins)
                bounds.append(bbox)
            assert bounds[1][3] == bounds[2][3], bounds
        verified.append(str(path.relative_to(ROOT)))
    phrase_path = SET / 'Sprüche/Abschiedsspruch.json'
    phrase = json.loads(phrase_path.read_text(encoding='utf-8'))
    assert set(phrase) == {'theme', 'line'}
    assert phrase['theme'] == 'Museumstag' and isinstance(phrase['line'], str) and len(phrase['line']) <= 180
    verified.append(str(phrase_path.relative_to(ROOT)))
    return verified


def publish():
    assert not SET.exists(), 'Assets 20 already exists before materialization'
    materialize()
    files = validate()
    run('git', 'config', 'user.name', 'github-actions[bot]')
    run('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    run('git', 'add', '--', *files)
    run('git', 'commit', '-m', 'Assets 20: Museumstag Asset-Set')
    run('git', 'push', 'origin', 'HEAD:main')
    run('git', 'fetch', 'origin', 'main')
    run('git', 'reset', '--hard', 'origin/main')
    verified = validate()
    print(json.dumps({'verified': verified, 'mainSha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}))


if __name__ == '__main__':
    publish()
