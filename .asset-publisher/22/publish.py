from __future__ import annotations

import base64
import io
import json
import os
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / ".asset-publisher" / "22"
SET = ROOT / "BeamtenMonitorAvatar" / "Assets 22"
THEME = "Schachtag"
LINE = "Ich gehe zurück ans Schachbrett – der Feierabendzug ist bereits ordnungsgemäß genehmigt."
FILES = {
    "idle": (SET / "Avatar" / "Idle.png", (1024, 1536)),
    "actions": (SET / "Avatar" / "Actions.png", (1536, 1024)),
    "scene": (SET / "MonitorScene" / "MonitorScene.png", (1672, 941)),
    "bell": (SET / "Klingel" / "MonitorBell.png", (1254, 1254)),
}
JSON_PATH = SET / "Sprüche" / "Abschiedsspruch.json"


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def materialize() -> None:
    if SET.exists():
        raise RuntimeError(f"{SET} already exists; refusing to overwrite")
    for key, (target, _) in FILES.items():
        chunks = sorted((PARTS / "chunks").glob(f"{key}.part-*"))
        if not chunks:
            raise RuntimeError(f"missing chunks for {key}")
        encoded = "".join(p.read_text(encoding="ascii") for p in chunks)
        data = base64.b64decode(encoded, validate=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_bytes(data)
        os.replace(temp, target)
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps({"theme": THEME, "line": LINE}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def validate_png(path: Path, expected: tuple[int, int]) -> Image.Image:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"{path}: invalid PNG signature")
    with Image.open(io.BytesIO(data)) as probe:
        probe.verify()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.format != "PNG" or image.size != expected or image.mode != "RGBA":
            raise RuntimeError(f"{path}: got {image.format} {image.size} {image.mode}")
        alpha = image.getchannel("A")
        lo, hi = alpha.getextrema()
        if lo != 0 or hi == 0:
            raise RuntimeError(f"{path}: invalid alpha range {(lo, hi)}")
        return image.copy()


def validate() -> None:
    images = {key: validate_png(path, size) for key, (path, size) in FILES.items()}
    actions = images["actions"]
    boxes: list[tuple[int, int, int, int]] = []
    for row in range(2):
        for col in range(4):
            cell = actions.crop((col * 384, row * 512, (col + 1) * 384, (row + 1) * 512))
            bbox = cell.getchannel("A").getbbox()
            if bbox is None:
                raise RuntimeError(f"empty action cell {row},{col}")
            left, top, right, bottom = bbox
            margins = (left, top, 384 - right, 512 - bottom)
            if min(margins) < 20:
                raise RuntimeError(f"action cell {row},{col} margins {margins}")
            boxes.append(bbox)
    if boxes[1][3] != boxes[2][3]:
        raise RuntimeError(f"walk baselines differ: {boxes[1][3]} vs {boxes[2][3]}")

    obj = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if set(obj) != {"theme", "line"} or obj["theme"] != THEME:
        raise RuntimeError("invalid farewell JSON structure")
    if not isinstance(obj["line"], str) or not obj["line"] or len(obj["line"]) > 180:
        raise RuntimeError("invalid farewell line")
    print(json.dumps({"validated": True, "cellBoxes": boxes, "minMargin": 25}, ensure_ascii=False))


def main() -> None:
    materialize()
    validate()
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    paths = [str(path.relative_to(ROOT)) for path, _ in FILES.values()] + [str(JSON_PATH.relative_to(ROOT))]
    subprocess.check_call(["git", "add", "--", *paths], cwd=ROOT)
    subprocess.check_call(["git", "commit", "-m", "Assets 22: Schachtag Asset-Set"], cwd=ROOT)
    asset_sha = run("git", "rev-parse", "HEAD")
    subprocess.check_call(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    subprocess.check_call(["git", "fetch", "origin", "main"], cwd=ROOT)
    subprocess.check_call(["git", "reset", "--hard", "origin/main"], cwd=ROOT)
    if run("git", "rev-parse", "HEAD") != asset_sha:
        raise RuntimeError("origin/main does not point to the published asset commit")
    validate()
    print(json.dumps({"postPushVerified": True, "mainSha": asset_sha}))


if __name__ == "__main__":
    main()
