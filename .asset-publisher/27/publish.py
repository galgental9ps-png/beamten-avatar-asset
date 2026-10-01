from __future__ import annotations

import base64, json, os, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / ".asset-publisher" / "27" / "chunks"
SET_ROOT = ROOT / "BeamtenMonitorAvatar" / "Assets 27"
THEME = "Eisenbahntag"
LINE = "Ich gehe zurück zum Bahnsteig – der Feierabendfahrplan ist ordnungsgemäß abgestempelt."
FILES = {
    "idle": (SET_ROOT / "Avatar" / "Idle.png", (1024, 1536), 1032968),
    "actions": (SET_ROOT / "Avatar" / "Actions.png", (1536, 1024), 1169664),
    "scene": (SET_ROOT / "MonitorScene" / "MonitorScene.png", (1672, 941), 1003679),
    "bell": (SET_ROOT / "Klingel" / "MonitorBell.png", (1254, 1254), 1528766),
}

def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()

def materialize() -> None:
    if SET_ROOT.exists(): raise RuntimeError(f"Zielordner existiert bereits: {SET_ROOT}")
    for name, (path, _, expected) in FILES.items():
        parts = sorted(CHUNKS.glob(f"{name}.b64.part-*"))
        if not parts: raise RuntimeError(f"Keine Chunks für {name}")
        raw = base64.b64decode("".join(p.read_text(encoding="ascii") for p in parts), validate=True)
        if len(raw) != expected: raise RuntimeError(f"Größe {name}: {len(raw)} != {expected}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("wb") as h: h.write(raw); h.flush(); os.fsync(h.fileno())
        os.replace(tmp, path)
    p = SET_ROOT / "Sprüche" / "Abschiedsspruch.json"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"theme": THEME, "line": LINE}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def validate_png(path: Path, expected: tuple[int, int]) -> None:
    if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n": raise RuntimeError(f"PNG-Signatur: {path}")
    with Image.open(path) as probe: probe.verify()
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected or image.mode != "RGBA": raise RuntimeError(f"PNG-Metadaten: {path}")
        lo, hi = image.getchannel("A").getextrema()
        if lo != 0 or hi == 0: raise RuntimeError(f"Transparenz: {path}, {(lo, hi)}")

def validate_actions(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        image.load(); boxes=[]; margins=[]; bottoms=[]
        for i in range(8):
            c, r = i % 4, i // 4
            box = image.crop((c*384, r*512, (c+1)*384, (r+1)*512)).getchannel("A").getbbox()
            if box is None: raise RuntimeError(f"Leere Sprite-Zelle {i}")
            m=[box[0],box[1],384-box[2],512-box[3]]
            if min(m)<20: raise RuntimeError(f"Sprite-Rand {i}: {m}")
            boxes.append(list(box)); margins.append(m)
            if i in (1,2): bottoms.append(box[3])
        if len(set(bottoms)) != 1: raise RuntimeError(f"Geh-Bodenlinien: {bottoms}")
        return {"bboxes":boxes,"margins":margins,"minMargin":min(min(x) for x in margins),"walkBaseline":bottoms[0]}

def validate_all() -> dict[str, object]:
    for _, (path, expected, size) in FILES.items():
        if path.stat().st_size != size: raise RuntimeError(f"Dateigröße: {path}")
        validate_png(path, expected)
    data=json.loads((SET_ROOT/"Sprüche"/"Abschiedsspruch.json").read_text(encoding="utf-8"))
    if list(data) != ["theme","line"] or data != {"theme":THEME,"line":LINE} or len(LINE)>180: raise RuntimeError("Spruch-JSON")
    return validate_actions(FILES["actions"][0])

def main() -> None:
    materialize(); before=validate_all()
    run("git","config","user.name","github-actions[bot]"); run("git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com")
    paths=[str(p.relative_to(ROOT)) for p,_,_ in FILES.values()]+[str((SET_ROOT/"Sprüche"/"Abschiedsspruch.json").relative_to(ROOT))]
    run("git","add","--",*paths); run("git","commit","-m","Assets 27: Eisenbahntag Asset-Set")
    asset=run("git","rev-parse","HEAD"); run("git","push","origin","HEAD:main")
    run("git","fetch","origin","main"); run("git","reset","--hard","origin/main")
    after=validate_all(); main=run("git","rev-parse","HEAD")
    if main != asset: raise RuntimeError(f"Post-Push-SHA {main} != {asset}")
    print(json.dumps({"assetSha":asset,"mainSha":main,"before":before,"after":after},ensure_ascii=False))

if __name__ == "__main__": main()
