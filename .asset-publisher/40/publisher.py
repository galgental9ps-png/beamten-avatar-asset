from pathlib import Path
from PIL import Image, ImageChops
import base64, hashlib, json, os, subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OUT=REPO/'BeamtenMonitorAvatar'/'Assets 40'
MAN=json.loads((HERE/'manifest.json').read_text(encoding='utf-8'))

def run(*args): subprocess.run(args,cwd=REPO,check=True)

def reconstruct():
    if OUT.exists(): raise RuntimeError('Assets 40 already exists')
    for item in MAN['files']:
        data=base64.b64decode(''.join((HERE/'chunks'/n).read_text() for n in item['chunks']),validate=True)
        assert len(data)==item['size'] and hashlib.sha256(data).hexdigest()==item['sha256']
        p=OUT/item['rel']; p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_suffix('.png.tmp')
        with open(tmp,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    p=OUT/'Sprüche/Abschiedsspruch.json'; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(MAN['json'],ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def verify_all():
    sizes={'Avatar/Idle.png':(1024,1536),'Avatar/Actions.png':(1536,1024),'MonitorScene/MonitorScene.png':(1672,941),'Klingel/MonitorBell.png':(1254,1254)}
    for rel,size in sizes.items():
        p=OUT/rel
        with Image.open(p) as im:
            im.load(); assert im.format=='PNG' and im.size==size and im.mode=='RGBA'
            lo,hi=im.getchannel('A').getextrema(); assert lo==0 and hi>0
        with Image.open(p) as im: im.verify()
    with Image.open(OUT/'Avatar/Idle.png') as im:
        b=im.getchannel('A').getbbox(); assert b and min(b[0],b[1],1024-b[2],1536-b[3])>=40
    with Image.open(OUT/'Avatar/Actions.png') as im:
        im.load(); crops=[]; margins=[]
        for row in range(2):
          for col in range(4):
            c=im.crop((col*384,row*512,(col+1)*384,(row+1)*512)); crops.append(c)
            b=c.getchannel('A').getbbox(); assert b
            m=(b[0],384-b[2],b[1],512-b[3]); margins.append(m); assert min(m)>=20
        assert ImageChops.difference(crops[1],crops[2]).getbbox()
        assert crops[1].getchannel('A').getbbox()[3]==crops[2].getchannel('A').getbbox()[3]
    data=json.loads((OUT/'Sprüche/Abschiedsspruch.json').read_text(encoding='utf-8'))
    assert list(data)==['theme','line'] and data['theme']=='Buchbindertag' and 0<len(data['line'])<=180
    print('VERIFIED',margins,data)

def main():
    reconstruct(); verify_all()
    paths=[str(OUT/rel) for rel in ['Avatar/Idle.png','Avatar/Actions.png','MonitorScene/MonitorScene.png','Klingel/MonitorBell.png','Sprüche/Abschiedsspruch.json']]
    run('git','config','user.name','github-actions[bot]'); run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','--',*paths)
    staged=subprocess.check_output(['git','-c','core.quotepath=false','diff','--cached','--name-only'],cwd=REPO,text=True).splitlines()
    expected=sorted(str(Path('BeamtenMonitorAvatar')/'Assets 40'/rel) for rel in ['Avatar/Idle.png','Avatar/Actions.png','MonitorScene/MonitorScene.png','Klingel/MonitorBell.png','Sprüche/Abschiedsspruch.json'])
    assert sorted(staged)==expected,(staged,expected)
    run('git','commit','-m','Assets 40: Buchbindertag (verified fallback publish)')
    run('git','push','origin','HEAD:main')
    run('git','fetch','origin','main'); run('git','reset','--hard','origin/main')
    verify_all(); print('POST_PUSH_ORIGIN_MAIN_VERIFIED',subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip())

if __name__=='__main__': main()
