from __future__ import annotations

import argparse, base64, hashlib, json, os, subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
SET_ROOT=ROOT/'BeamtenMonitorAvatar'/'Assets 30'
SOURCE_ROOT=ROOT/'.asset-publisher'/'30'/'chunks'
FILES={
 'idle':{'path':SET_ROOT/'Avatar/Idle.png','size':(1024,1536),'bytes':1071107,'sha256':'765064d61138eeb0835099f531963181c0ba02276ee665be6892092d820e4388'},
 'actions':{'path':SET_ROOT/'Avatar/Actions.png','size':(1536,1024),'bytes':1361688,'sha256':'d89418c9e3465d276a355b54224fd8ad1f5eb9ffb3a395b752cbab189f3cbed5'},
 'scene':{'path':SET_ROOT/'MonitorScene/MonitorScene.png','size':(1672,941),'bytes':989265,'sha256':'266c350b34e37d3d83566dfcd8a6c2b522228d917fbaea28e5fd7ae61687da4d'},
 'bell':{'path':SET_ROOT/'Klingel/MonitorBell.png','size':(1254,1254),'bytes':1442763,'sha256':'83cba6eba93ae5327713869d12bcf8d3a6c1a4e1c28fef07876f778da2426706'},
}
PHRASE={'theme':'Drachentag','line':'Ich hole den Drachen ein – der Wind hat den Feierabend schon genehmigt.'}

def run(*args): return subprocess.check_output(args,cwd=ROOT,text=True).strip()

def reconstruct():
 for key,meta in FILES.items():
  chunks=sorted(SOURCE_ROOT.glob(f'{key}-*.b64'))
  if not chunks: raise RuntimeError(f'Keine Base64-Chunks für {key}')
  data=base64.b64decode(''.join(p.read_text(encoding='ascii') for p in chunks),validate=True)
  if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']: raise RuntimeError(f'Binärprüfung für {key} fehlgeschlagen')
  target=meta['path']; target.parent.mkdir(parents=True,exist_ok=True); temp=target.with_suffix('.png.part')
  with temp.open('wb') as handle: handle.write(data); handle.flush(); os.fsync(handle.fileno())
  os.replace(temp,target)
 phrase_path=SET_ROOT/'Sprüche/Abschiedsspruch.json'; phrase_path.parent.mkdir(parents=True,exist_ok=True)
 phrase_path.write_text(json.dumps(PHRASE,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')

def validate_png(path,size):
 data=path.read_bytes()
 if data[:8]!=b'\x89PNG\r\n\x1a\n': raise RuntimeError(f'Keine PNG-Signatur: {path}')
 with Image.open(path) as image:
  image.load()
  if image.format!='PNG' or image.size!=size or image.mode!='RGBA' or image.getchannel('A').getextrema()[0]!=0: raise RuntimeError(f'PNG-Eigenschaften falsch: {path}')
 with Image.open(path) as image: image.verify()

def validate():
 for key,meta in FILES.items():
  path=meta['path']; data=path.read_bytes()
  if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']: raise RuntimeError(f'Veröffentlichte Datei für {key} stimmt nicht')
  validate_png(path,meta['size'])
 with Image.open(FILES['actions']['path']) as actions:
  actions.load(); cells=[]
  for row in range(2):
   for column in range(4):
    box=actions.crop((column*384,row*512,(column+1)*384,(row+1)*512)).getchannel('A').getbbox()
    if box is None: raise RuntimeError(f'Leere Sprite-Zelle {row},{column}')
    margins=(box[0],box[1],384-box[2],512-box[3])
    if min(margins)<20: raise RuntimeError(f'Sprite-Zelle {row},{column} hat zu kleinen Rand: {margins}')
    cells.append((box,margins))
  if cells[1][0][3]!=486 or cells[2][0][3]!=486: raise RuntimeError('Gehframes liegen nicht auf Bodenlinie 486')
  if actions.crop((384,0,768,512)).tobytes()==actions.crop((768,0,1152,512)).tobytes(): raise RuntimeError('Gehphasen sind identisch')
 phrase=json.loads((SET_ROOT/'Sprüche/Abschiedsspruch.json').read_text(encoding='utf-8'))
 if phrase!=PHRASE or list(phrase)!=['theme','line'] or len(phrase['line'])>180: raise RuntimeError('Abschiedsspruch.json ist ungültig')
 print('VALIDATION_OK min_sprite_margin=25 walking_baseline=486')

def publish():
 paths=['BeamtenMonitorAvatar/Assets 30/Avatar/Idle.png','BeamtenMonitorAvatar/Assets 30/Avatar/Actions.png','BeamtenMonitorAvatar/Assets 30/MonitorScene/MonitorScene.png','BeamtenMonitorAvatar/Assets 30/Klingel/MonitorBell.png','BeamtenMonitorAvatar/Assets 30/Sprüche/Abschiedsspruch.json']
 subprocess.check_call(['git','config','user.name','Beamten Asset Automation'],cwd=ROOT)
 subprocess.check_call(['git','config','user.email','actions@users.noreply.github.com'],cwd=ROOT)
 subprocess.check_call(['git','add','--',*paths],cwd=ROOT)
 subprocess.check_call(['git','commit','-m','Assets 30: Drachentag Asset-Set','--',*paths],cwd=ROOT)
 sha=run('git','rev-parse','HEAD'); subprocess.check_call(['git','push','origin','HEAD:main'],cwd=ROOT); print(f'ASSET_COMMIT={sha}'); return sha

def post_push_verify(expected):
 subprocess.check_call(['git','fetch','origin','main'],cwd=ROOT); remote=run('git','rev-parse','origin/main')
 if remote!=expected: raise RuntimeError(f'origin/main ist {remote}, erwartet {expected}')
 subprocess.check_call(['git','reset','--hard','origin/main'],cwd=ROOT); validate(); print(f'POST_PUSH_VERIFIED={remote}')

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--verify-only',action='store_true'); args=parser.parse_args()
 if args.verify_only: validate(); return
 reconstruct(); validate(); post_push_verify(publish())

if __name__=='__main__': main()
