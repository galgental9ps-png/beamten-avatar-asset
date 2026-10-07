from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
TARGET = REPO / MANIFEST["target"]
JSON_REL = "Sprüche/Abschiedsspruch.json"
EXPECTED = {
    "Avatar/Idle.png": (1024, 1536),
    "Avatar/Actions.png": (1536, 1024),
    "MonitorScene/MonitorScene.png": (1672, 941),
    "Klingel/MonitorBell.png": (1254, 1254),
}


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=REPO, text=True).strip()


def reconstruct() -> None:
    if TARGET.exists():
        raise RuntimeError(f"refusing to overwrite existing target: {TARGET}")
    for rel, meta in MANIFEST["assets"].items():
        encoded = "".join((HERE / "chunks" / name).read_text(encoding="ascii") for name in meta["chunks"])
        data = base64.b64decode(encoded, validate=True)
        if len(data) != meta["size"]:
            raise RuntimeError(f"size mismatch before write: {rel}")
        if hashlib.sha256(data).hexdigest() != meta["sha256"]:
            raise RuntimeError(f"sha256 mismatch before write: {rel}")
        path = TARGET / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    out = TARGET / JSON_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(MANIFEST["farewell"], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def verify_png(path: Path, expected_size: tuple[int, int]) -> None:
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected_size or image.mode != "RGBA":
            raise RuntimeError(f"invalid PNG metadata: {path}: {image.format} {image.size} {image.mode}")
        lo, hi = image.getchannel("A").getextrema()
        if lo != 0 or hi == 0:
            raise RuntimeError(f"missing real transparency: {path}: {(lo, hi)}")
    with Image.open(path) as image:
        image.verify()


def alpha_bbox(frame: Image.Image) -> tuple[int, int, int, int]:
    bbox = frame.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("empty sprite cell")
    return bbox


def verify_all() -> None:
    for rel, size in EXPECTED.items():
        path = TARGET / rel
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"missing or empty file: {path}")
        verify_png(path, size)
        expected_hash = MANIFEST["assets"][rel]["sha256"]
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeError(f"published bytes differ from manifest: {rel}")

    with Image.open(TARGET / "Avatar/Actions.png") as sheet:
        sheet = sheet.convert("RGBA")
        boxes = []
        for row in range(2):
            for col in range(4):
                frame = sheet.crop((col * 384, row * 512, (col + 1) * 384, (row + 1) * 512))
                left, top, right, bottom = alpha_bbox(frame)
                margins = (left, 384 - right, top, 512 - bottom)
                if min(margins) < 20:
                    raise RuntimeError(f"sprite cell {row},{col} margin below 20 px: {margins}")
                boxes.append((left, top, right, bottom))
        if boxes[1][3] != boxes[2][3]:
            raise RuntimeError(f"walking baselines differ: {boxes[1][3]} vs {boxes[2][3]}")
        walk1 = sheet.crop((384, 0, 768, 512))
        walk2 = sheet.crop((768, 0, 1152, 512))
        if ImageChops.difference(walk1, walk2).getbbox() is None:
            raise RuntimeError("walking frames are identical")

    farewell_path = TARGET / JSON_REL
    farewell = json.loads(farewell_path.read_text(encoding="utf-8"))
    if list(farewell) != ["theme", "line"] or farewell["theme"] != MANIFEST["theme"]:
        raise RuntimeError("farewell JSON fields or theme invalid")
    if not isinstance(farewell["line"], str) or not farewell["line"] or len(farewell["line"]) > 180:
        raise RuntimeError("farewell line invalid")
    print("verified", MANIFEST["target"], "all five files")


def publish() -> None:
    reconstruct()
    verify_all()
    asset_paths = [str(Path(MANIFEST["target"]) / rel) for rel in [*EXPECTED, JSON_REL]]
    subprocess.check_call(["git", "add", "--", *asset_paths], cwd=REPO)
    staged = run("git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only").splitlines()
    if sorted(staged) != sorted(asset_paths):
        raise RuntimeError(f"atomic commit path mismatch: {staged}")
    subprocess.check_call(["git", "commit", "-m", "Assets 33: Schneidertag Asset-Set"], cwd=REPO)
    asset_sha = run("git", "rev-parse", "HEAD")
    subprocess.check_call(["git", "push", "origin", "HEAD:main"], cwd=REPO)
    subprocess.check_call(["git", "fetch", "origin", "main"], cwd=REPO)
    subprocess.check_call(["git", "reset", "--hard", "origin/main"], cwd=REPO)
    if run("git", "rev-parse", "HEAD") != asset_sha:
        raise RuntimeError("origin/main does not point at the asset commit")
    verify_all()
    print("ASSET_COMMIT_SHA=" + asset_sha)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        verify_all()
    else:
        publish()
