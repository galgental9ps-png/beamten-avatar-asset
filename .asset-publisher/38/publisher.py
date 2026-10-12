from pathlib import Path
from PIL import Image
import base64, hashlib, json, os, subprocess

ROOT=Path('.')
PUB=ROOT/'.asset-publisher/38'
TARGET=ROOT/'BeamtenMonitorAvatar/Assets 38'
EXPECTED={
 'Avatar/Idle.png':(1024,1536),
 'Avatar/Actions.png':(1536,1024),
 'MonitorScene/MonitorScene.png':(1672,941),
 'Klingel/MonitorBell.png':(1254,1254),
}

def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    with open(tmp,'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def reconstruct():
    m=json.loads((PUB/'manifest.json').read_text('utf-8'))
    assert m['target']=='BeamtenMonitorAvatar/Assets 38'
    for rel,meta in m['files'].items():
        text=''.join((PUB/'chunks'/name).read_text('ascii') for name in meta['chunks'])
        raw=base64.b64decode(text,validate=True)
        assert len(raw)==meta['size'],(rel,len(raw),meta['size'])
        assert hashlib.sha256(raw).hexdigest()==meta['sha256'],rel
        atomic_write(TARGET/rel,raw)
    farewell={'theme':'Kürbistag','line':'Ich gehe dann zurück – der Feierabend ist heute amtlich ausgehöhlt und freigegeben!'}
    atomic_write(TARGET/'Sprüche/Abschiedsspruch.json',json.dumps(farewell,ensure_ascii=False,separators=(',',':')).encode('utf-8'))

def verify_all():
    for rel,size in EXPECTED.items():
        p=TARGET/rel
        with Image.open(p) as im:
            im.load()
            assert im.format=='PNG' and im.size==size and im.mode=='RGBA',(rel,im.format,im.size,im.mode)
            assert im.getchannel('A').getextrema()[0]==0,rel
        with Image.open(p) as im: im.verify()
    with Image.open(TARGET/'Avatar/Actions.png') as im:
        im.load(); boxes=[]
        for r in range(2):
            for c in range(4):
                cr=im.crop((c*384,r*512,(c+1)*384,(r+1)*512))
                box=cr.getchannel('A').point(lambda x:255 if x>8 else 0).getbbox()
                assert box is not None,(r,c)
                l,t,rr,b=box
                margins=(l,384-rr,t,512-b)
                assert min(margins)>=20,(r,c,box,margins)
                boxes.append(box)
        assert boxes[1][3]==boxes[2][3],(boxes[1],boxes[2])
        assert im.crop((384,0,768,512)).tobytes()!=im.crop((768,0,1152,512)).tobytes()
    j=json.loads((TARGET/'Sprüche/Abschiedsspruch.json').read_text('utf-8'))
    assert list(j)==['theme','line'] and j['theme']=='Kürbistag' and len(j['line'])<=180

def sh(*args):
    subprocess.run(args,check=True)

if __name__=='__main__':
    reconstruct()
    verify_all()
    paths=[str(TARGET/x) for x in [*EXPECTED,'Sprüche/Abschiedsspruch.json']]
    sh('git','add','--',*paths)
    sh('git','config','user.name','github-actions[bot]')
    sh('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    sh('git','commit','-m','Assets 38: Kürbistag (verified fallback publish)')
    sh('git','push','origin','HEAD:main')
    sh('git','fetch','origin','main')
    sh('git','reset','--hard','origin/main')
    verify_all()
    print('POST_PUSH_VERIFIED_MAIN_SHA='+subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
