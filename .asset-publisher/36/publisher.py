from pathlib import Path
from PIL import Image, ImageChops
import base64, hashlib, json, os, subprocess

ROOT = Path.cwd()
PUB = ROOT / '.asset-publisher/36'
TARGET = ROOT / 'BeamtenMonitorAvatar/Assets 36'
FILES = [
    'BeamtenMonitorAvatar/Assets 36/Avatar/Idle.png',
    'BeamtenMonitorAvatar/Assets 36/Avatar/Actions.png',
    'BeamtenMonitorAvatar/Assets 36/MonitorScene/MonitorScene.png',
    'BeamtenMonitorAvatar/Assets 36/Klingel/MonitorBell.png',
    'BeamtenMonitorAvatar/Assets 36/Sprüche/Abschiedsspruch.json',
]
SIZES = {
    'Avatar/Idle.png': (1024, 1536),
    'Avatar/Actions.png': (1536, 1024),
    'MonitorScene/MonitorScene.png': (1672, 941),
    'Klingel/MonitorBell.png': (1254, 1254),
}

def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def reconstruct():
    manifest = json.loads((PUB / 'manifest.json').read_text(encoding='utf-8'))
    for rel, meta in manifest['pngs'].items():
        payload = ''.join((PUB / 'chunks' / name).read_text(encoding='ascii') for name in meta['chunks'])
        raw = base64.b64decode(payload, validate=True)
        assert len(raw) == meta['size'], (rel, len(raw), meta['size'])
        assert hashlib.sha256(raw).hexdigest() == meta['sha256'], rel
        atomic_write(ROOT / rel, raw)
    phrase = {'theme':'Puzzletag','line':'Ich gehe dann zurück – der Feierabend ist jetzt lückenlos zusammengesetzt und genehmigt!'}
    atomic_write(TARGET / 'Sprüche/Abschiedsspruch.json', (json.dumps(phrase, ensure_ascii=False, separators=(',', ':'))+'\n').encode())

def verify_all():
    for rel, size in SIZES.items():
        p = TARGET / rel
        with Image.open(p) as im:
            im.load()
            assert im.format == 'PNG' and im.size == size and im.mode == 'RGBA', (rel, im.format, im.size, im.mode)
            lo, hi = im.getchannel('A').getextrema()
            assert lo == 0 and hi > 0, (rel, lo, hi)
        with Image.open(p) as im:
            im.verify()
    with Image.open(TARGET / 'Avatar/Actions.png') as im:
        a = im.getchannel('A'); boxes=[]; crops=[]
        for row in range(2):
            for col in range(4):
                crop = a.crop((col*384,row*512,(col+1)*384,(row+1)*512))
                box = crop.point(lambda v: 255 if v > 8 else 0).getbbox()
                assert box is not None
                margins = (box[0],384-box[2],box[1],512-box[3])
                assert min(margins) >= 20, (row,col,box,margins)
                boxes.append(box); crops.append(crop)
        assert boxes[1][3] == boxes[2][3], (boxes[1], boxes[2])
        assert ImageChops.difference(crops[1], crops[2]).getbbox() is not None
    data = json.loads((TARGET / 'Sprüche/Abschiedsspruch.json').read_text(encoding='utf-8'))
    assert list(data) == ['theme','line'] and data['theme'] == 'Puzzletag'
    assert isinstance(data['line'], str) and 0 < len(data['line']) <= 180

def main():
    reconstruct(); verify_all()
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','--',*FILES)
    staged = subprocess.check_output(['git','-c','core.quotepath=false','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    assert sorted(staged) == sorted(FILES), staged
    run('git','commit','-m','Assets 36: Puzzletag Asset-Set')
    asset_sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    run('git','push','origin','HEAD:main')
    run('git','fetch','origin','main')
    run('git','reset','--hard','origin/main')
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == asset_sha
    verify_all()
    print('ASSET_COMMIT='+asset_sha)

if __name__ == '__main__':
    main()
