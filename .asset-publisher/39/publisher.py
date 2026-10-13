from pathlib import Path
from PIL import Image
import base64,hashlib,json,os,subprocess
ROOT=Path('.'); PUB=ROOT/'.asset-publisher/39'; TARGET=ROOT/'BeamtenMonitorAvatar/Assets 39'
EXPECTED={'Avatar/Idle.png':(1024,1536),'Avatar/Actions.png':(1536,1024),'MonitorScene/MonitorScene.png':(1672,941),'Klingel/MonitorBell.png':(1254,1254)}
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
 with open(tmp,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,path)
def reconstruct():
 m=json.loads((PUB/'manifest.json').read_text('utf-8')); assert m['target']=='BeamtenMonitorAvatar/Assets 39'
 for rel,meta in m['files'].items():
  raw=base64.b64decode(''.join((PUB/'chunks'/x).read_text('ascii') for x in meta['chunks']),validate=True)
  assert len(raw)==meta['size'] and hashlib.sha256(raw).hexdigest()==meta['sha256'],rel
  atomic(TARGET/rel,raw)
 atomic(TARGET/'Sprüche/Abschiedsspruch.json',json.dumps({'theme':'Laternentag','line':'Ich gehe dann zurück – die Akten sind für heute eingeleuchtet und der Feierabend ist freigegeben!'},ensure_ascii=False,separators=(',',':')).encode('utf-8'))
def verify_all():
 for rel,size in EXPECTED.items():
  p=TARGET/rel
  with Image.open(p) as im:
   im.load(); assert im.format=='PNG' and im.size==size and im.mode=='RGBA'; assert im.getchannel('A').getextrema()[0]==0
  with Image.open(p) as im: im.verify()
 with Image.open(TARGET/'Avatar/Actions.png') as im:
  im.load(); boxes=[]
  for r in range(2):
   for c in range(4):
    cr=im.crop((c*384,r*512,(c+1)*384,(r+1)*512)); b=cr.getchannel('A').point(lambda x:255 if x>8 else 0).getbbox(); assert b
    l,t,rr,bb=b; assert min(l,384-rr,t,512-bb)>=20,(r,c,b)
    boxes.append(b)
  assert boxes[1][3]==boxes[2][3]
  assert im.crop((384,0,768,512)).tobytes()!=im.crop((768,0,1152,512)).tobytes()
 j=json.loads((TARGET/'Sprüche/Abschiedsspruch.json').read_text('utf-8')); assert list(j)==['theme','line'] and j['theme']=='Laternentag' and len(j['line'])<=180
def sh(*args): subprocess.run(args,check=True)
if __name__=='__main__':
 reconstruct(); verify_all()
 paths=[str(TARGET/x) for x in [*EXPECTED,'Sprüche/Abschiedsspruch.json']]
 sh('git','add','--',*paths); sh('git','config','user.name','github-actions[bot]'); sh('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 sh('git','commit','-m','Assets 39: Laternentag (verified fallback publish)'); sh('git','push','origin','HEAD:main')
 sh('git','fetch','origin','main'); sh('git','reset','--hard','origin/main'); verify_all()
 print('POST_PUSH_VERIFIED_MAIN_SHA='+subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
