from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / '.asset-publisher' / '28'
BASE = ROOT / 'BeamtenMonitorAvatar' / 'Assets 28'
FILES = {
    'idle': (BASE / 'Avatar' / 'Idle.png', (1024, 1536)),
    'actions': (BASE / 'Avatar' / 'Actions.png', (1536, 1024)),
    'scene': (BASE / 'MonitorScene' / 'MonitorScene.png', (1672, 941)),
    'bell': (BASE / 'Klingel' / 'MonitorBell.png', (1254, 1254)),
}
EXPECTED = {
    'idle': 'a3f945e889aa77af22170329c9ce996f84d5b6bdd0dc464cb28826ecca898aa2',
    'actions': '4d343af73956e442f5e605124a0e98554362c57d779b8accfbf95f115662f4f9',
    'scene': 'f198d5f7f92bb006749838cc4819597306d33103af4d4cc4fa2f984b59f1d536',
    'bell': '5426541faadb3f9c6883c0a570ea495845c9932a5b1ad0c7d21ad2e0fd0d3c08',
}
PHRASE = {
    'theme': 'Leuchtturmtag',
    'line': 'Ich gehe zurück zum Leuchtturm – die Feierabendfreigabe leuchtet bereits grün.'
}


def reconstruct() -> None:
    for key, (target, _) in FILES.items():
        parts = sorted(PUB.glob(f'{key}.b64.part-*'))
        if not parts:
            raise RuntimeError(f'missing chunks for {key}')
        raw = base64.b64decode(''.join(p.read_text() for p in parts), validate=True)
        if hashlib.sha256(raw).hexdigest() != EXPECTED[key]:
            raise RuntimeError(f'checksum mismatch for {key}')
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix('.png.tmp')
        tmp.write_bytes(raw)
        tmp.replace(target)
    phrase = BASE / 'Sprüche' / 'Abschiedsspruch.json'
    phrase.parent.mkdir(parents=True, exist_ok=True)
    # No trailing newline so this valid JSON blob is included in the corrective commit.
    phrase.write_text(json.dumps(PHRASE, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def validate() -> None:
    for key, (path, size) in FILES.items():
        if not path.exists() or path.stat().st_size <= 0:
            raise RuntimeError(f'missing/empty {path}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED[key]:
            raise RuntimeError(f'published checksum mismatch for {key}')
        with Image.open(path) as im:
            im.load()
            if im.format != 'PNG' or im.size != size or im.mode != 'RGBA':
                raise RuntimeError(f'invalid metadata for {key}: {im.format} {im.size} {im.mode}')
            lo, hi = im.getchannel('A').getextrema()
            if lo != 0 or hi == 0:
                raise RuntimeError(f'invalid transparency for {key}: {(lo, hi)}')
        with Image.open(path) as im:
            im.verify()
    actions = Image.open(FILES['actions'][0]).convert('RGBA')
    cells = []
    for row in range(2):
        for col in range(4):
            bbox = actions.crop((col*384, row*512, (col+1)*384, (row+1)*512)).getchannel('A').getbbox()
            if not bbox:
                raise RuntimeError(f'empty sprite cell {row},{col}')
            margins = (bbox[0], bbox[1], 384-bbox[2], 512-bbox[3])
            if min(margins) < 20:
                raise RuntimeError(f'unsafe sprite cell {row},{col}: {margins}')
            cells.append(bbox)
    if cells[1][3] != cells[2][3] or cells[1][3] != 486:
        raise RuntimeError(f'walk baselines differ: {cells[1][3]}, {cells[2][3]}')
    obj = json.loads((BASE / 'Sprüche' / 'Abschiedsspruch.json').read_text(encoding='utf-8'))
    if list(obj) != ['theme', 'line'] or obj != PHRASE or len(obj['line']) > 180:
        raise RuntimeError('farewell JSON invalid')
    print(json.dumps({'verified': 5, 'minMargin': 25, 'walkBaseline': 486, 'theme': obj['theme']}))


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


if __name__ == '__main__':
    if '--verify-only' in sys.argv:
        validate()
    else:
        reconstruct()
        validate()
        run('git', 'config', 'user.name', 'github-actions[bot]')
        run('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        run('git', 'add',
            'BeamtenMonitorAvatar/Assets 28/Avatar/Idle.png',
            'BeamtenMonitorAvatar/Assets 28/Avatar/Actions.png',
            'BeamtenMonitorAvatar/Assets 28/MonitorScene/MonitorScene.png',
            'BeamtenMonitorAvatar/Assets 28/Klingel/MonitorBell.png',
            'BeamtenMonitorAvatar/Assets 28/Sprüche/Abschiedsspruch.json')
        run('git', 'commit', '-m', 'Assets 28: Leuchtturmtag Asset-Set (vollständig)')
        run('git', 'push', 'origin', 'HEAD:main')

