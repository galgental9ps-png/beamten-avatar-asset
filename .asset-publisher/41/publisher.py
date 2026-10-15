from pathlib import Path
from PIL import Image, ImageChops
import base64, hashlib, json, subprocess

STAGE = Path('.asset-publisher/41')
MANIFEST = json.loads((STAGE/'manifest.json').read_text('utf-8'))
BASE = Path('BeamtenMonitorAvatar/Assets 41')
PNG_SPECS = {
 'Avatar/Idle.png': (1024,1536), 'Avatar/Actions.png': (1536,1024),
 'MonitorScene/MonitorScene.png': (1672,941), 'Klingel/MonitorBell.png': (1254,1254)}
JSON_REL = 'Sprüche/Abschiedsspruch.json'
EXPECTED = [str(BASE/p) for p in [*PNG_SPECS, JSON_REL]]

def sh(*args):
    return subprocess.check_output(args, text=True).strip()

def reconstruct():
    for item in MANIFEST['files']:
        raw = base64.b64decode(''.join((STAGE/c).read_text('ascii') for c in item['chunks']))
        assert len(raw) == item['size'] and hashlib.sha256(raw).hexdigest() == item['sha256']
        p = BASE/item['path']; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    p = BASE/JSON_REL; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(MANIFEST['speech'],ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def alpha_bbox(im):
    return im.getchannel('A').point(lambda v: 255 if v >= 18 else 0).getbbox()

def verify():
    actual = sorted(str(p) for p in BASE.rglob('*') if p.is_file())
    assert actual == sorted(EXPECTED), (actual, EXPECTED)
    for rel, size in PNG_SPECS.items():
        p=BASE/rel
        with Image.open(p) as im:
            im.load(); assert im.format=='PNG' and im.size==size and im.mode=='RGBA'
            lo,hi=im.getchannel('A').getextrema(); assert lo==0 and hi>0
        with Image.open(p) as im: im.verify()
    with Image.open(BASE/'Avatar/Idle.png') as im:
        b=alpha_bbox(im); assert min(b[0],b[1],1024-b[2],1536-b[3])>=40
    margins=[]; cells=[]
    with Image.open(BASE/'Avatar/Actions.png') as im:
        for row in range(2):
            for col in range(4):
                c=im.crop((col*384,row*512,(col+1)*384,(row+1)*512)); cells.append(c.copy())
                b=alpha_bbox(c); assert b
                m=(b[0],b[1],384-b[2],512-b[3]); margins.append(m); assert min(m)>=20,(row,col,m)
    assert abs(alpha_bbox(cells[1])[3]-alpha_bbox(cells[2])[3])<=2
    assert ImageChops.difference(cells[1],cells[2]).getbbox() is not None
    obj=json.loads((BASE/JSON_REL).read_text('utf-8'))
    assert list(obj)==['theme','line'] and obj['theme']=='Zeitungstag' and len(obj['line'])<=180
    return min(map(min,margins))

reconstruct()
margin=verify()
subprocess.run(['git','config','user.name','beamten-avatar-automation'],check=True)
subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','add','--',*EXPECTED],check=True)
staged=sh('git','-c','core.quotepath=false','diff','--cached','--name-only').splitlines()
assert staged==EXPECTED,(staged,EXPECTED)
subprocess.run(['git','commit','-m','Assets 41: Zeitungstag (verified fallback publish)'],check=True)
asset_sha=sh('git','rev-parse','HEAD')
subprocess.run(['git','push','origin','HEAD:main'],check=True)
subprocess.run(['git','fetch','origin','main'],check=True)
subprocess.run(['git','reset','--hard','origin/main'],check=True)
assert sh('git','rev-parse','HEAD')==asset_sha
post_margin=verify(); assert post_margin==margin
print(json.dumps({'assetSha':asset_sha,'minCellMargin':margin,'postPushVerified':True}))

