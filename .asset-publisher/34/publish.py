from pathlib import Path
from PIL import Image, ImageChops
import base64, hashlib, json, os, subprocess

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / '.asset-publisher' / '34'
TARGET = ROOT / 'BeamtenMonitorAvatar' / 'Assets 34'

def run(*args):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()

def reconstruct():
    manifest = json.loads((CFG/'manifest.json').read_text(encoding='utf-8'))
    for rel, meta in manifest.items():
        encoded = ''.join((CFG/'chunks'/name).read_text(encoding='ascii') for name in meta['chunks'])
        data = base64.b64decode(encoded, validate=True)
        if len(data) != meta['size'] or hashlib.sha256(data).hexdigest() != meta['sha256']:
            raise ValueError(f'Binary integrity mismatch: {rel}')
        dst = ROOT/rel; dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix('.tmp.png'); tmp.write_bytes(data)
        with open(tmp,'rb') as f: os.fsync(f.fileno())
        os.replace(tmp,dst)
    phrase = {'theme':'Aquariumstag','line':'Ich tauche dann mal ab – der Feierabend ist schließlich ordnungsgemäß genehmigt!'}
    p=TARGET/'Sprüche/Abschiedsspruch.json'; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(phrase,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')

def verify_all():
    expected={
      TARGET/'Avatar/Idle.png':(1024,1536),
      TARGET/'Avatar/Actions.png':(1536,1024),
      TARGET/'MonitorScene/MonitorScene.png':(1672,941),
      TARGET/'Klingel/MonitorBell.png':(1254,1254),
    }
    for p,size in expected.items():
        if not p.is_file() or p.stat().st_size <= 0: raise ValueError(f'missing {p}')
        with Image.open(p) as im:
            im.load()
            if im.format!='PNG' or im.size!=size or im.mode!='RGBA': raise ValueError(f'invalid PNG {p}')
            if im.getchannel('A').getextrema()[0]!=0 or not im.getchannel('A').getbbox(): raise ValueError(f'invalid alpha {p}')
        with Image.open(p) as im: im.verify()
    actions=expected.keys().__iter__().__next__().parent/'Actions.png'
    with Image.open(actions) as im:
        im.load(); a=im.getchannel('A'); boxes=[]
        for row in range(2):
            for col in range(4):
                crop=a.crop((col*384,row*512,(col+1)*384,(row+1)*512)); b=crop.getbbox()
                if not b: raise ValueError(f'empty sprite cell {row},{col}')
                margins=(b[0],384-b[2],b[1],512-b[3])
                if min(margins)<20: raise ValueError(f'sprite margin {row},{col}: {margins}')
                boxes.append(b)
        if boxes[1][3] != boxes[2][3]: raise ValueError('walk baseline mismatch')
        if not ImageChops.difference(im.crop((384,0,768,512)),im.crop((768,0,1152,512))).getbbox(): raise ValueError('walk frames identical')
    phrase=json.loads((TARGET/'Sprüche/Abschiedsspruch.json').read_text(encoding='utf-8'))
    if list(phrase)!=['theme','line'] or phrase['theme']!='Aquariumstag' or len(phrase['line'])>180: raise ValueError('invalid phrase JSON')

def main():
    reconstruct(); verify_all()
    files=[
      'BeamtenMonitorAvatar/Assets 34/Avatar/Idle.png',
      'BeamtenMonitorAvatar/Assets 34/Avatar/Actions.png',
      'BeamtenMonitorAvatar/Assets 34/MonitorScene/MonitorScene.png',
      'BeamtenMonitorAvatar/Assets 34/Klingel/MonitorBell.png',
      'BeamtenMonitorAvatar/Assets 34/Sprüche/Abschiedsspruch.json',
    ]
    run('git','add','--',*files)
    staged=run('git','-c','core.quotepath=false','diff','--cached','--name-only').splitlines()
    if sorted(staged)!=sorted(files): raise ValueError(f'atomic asset path mismatch: {staged}')
    run('git','commit','-m','Assets 34: Aquariumstag Asset-Set')
    run('git','push','origin','HEAD:main')
    asset_sha=run('git','rev-parse','HEAD')
    run('git','fetch','origin','main')
    run('git','reset','--hard','origin/main')
    if run('git','rev-parse','HEAD')!=asset_sha: raise ValueError('origin/main SHA mismatch')
    verify_all()
    print(f'POST_PUSH_VERIFIED_SHA={asset_sha}')

if __name__=='__main__': main()
