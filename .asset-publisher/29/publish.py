from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SET_ROOT = ROOT / "BeamtenMonitorAvatar" / "Assets 29"
SOURCE_ROOT = ROOT / ".asset-publisher" / "29" / "chunks"

FILES = {
    "idle": {
        "path": SET_ROOT / "Avatar" / "Idle.png",
        "size": (1024, 1536),
        "bytes": 1139030,
        "sha256": "7dc288875cb8f8e36faaffe1f258ef0946688b57251c7a7cbad537e510f7ec6b",
    },
    "actions": {
        "path": SET_ROOT / "Avatar" / "Actions.png",
        "size": (1536, 1024),
        "bytes": 1331197,
        "sha256": "358b7043d08570fa0aad5fd29035110c74c8e0305737c8666297233359e8747f",
    },
    "scene": {
        "path": SET_ROOT / "MonitorScene" / "MonitorScene.png",
        "size": (1672, 941),
        "bytes": 1005157,
        "sha256": "c16f201bc88949ccca81d4e4fff92b182d263840629f51d56216b5809a5401f6",
    },
    "bell": {
        "path": SET_ROOT / "Klingel" / "MonitorBell.png",
        "size": (1254, 1254),
        "bytes": 1447682,
        "sha256": "9ae35737a11d2bf634b49af97a340c62bb7947dd440ff79636552a5db9beb80b",
    },
}

PHRASE = {
    "theme": "Kanutag",
    "line": "Ich paddle zurück zum Bootshaus – der Feierabendantrag ist bereits wasserdicht.",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def reconstruct() -> None:
    for key, meta in FILES.items():
        chunks = sorted(SOURCE_ROOT.glob(f"{key}-*.b64"))
        if not chunks:
            raise RuntimeError(f"Keine Base64-Chunks für {key}")
        encoded = "".join(p.read_text(encoding="ascii") for p in chunks)
        data = base64.b64decode(encoded, validate=True)
        if len(data) != meta["bytes"]:
            raise RuntimeError(f"Bytezahl für {key} falsch: {len(data)}")
        digest = hashlib.sha256(data).hexdigest()
        if digest != meta["sha256"]:
            raise RuntimeError(f"SHA-256 für {key} falsch: {digest}")
        target: Path = meta["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".png.part")
        with temp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)

    phrase_path = SET_ROOT / "Sprüche" / "Abschiedsspruch.json"
    phrase_path.parent.mkdir(parents=True, exist_ok=True)
    phrase_path.write_text(
        json.dumps(PHRASE, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def validate_png(path: Path, expected_size: tuple[int, int]) -> None:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Keine PNG-Signatur: {path}")
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected_size or image.mode != "RGBA":
            raise RuntimeError(
                f"PNG-Eigenschaften falsch: {path}: {image.format}, {image.size}, {image.mode}"
            )
        if image.getchannel("A").getextrema()[0] != 0:
            raise RuntimeError(f"Keine echten transparenten Pixel: {path}")
    with Image.open(path) as image:
        image.verify()


def validate() -> None:
    for key, meta in FILES.items():
        path: Path = meta["path"]
        if path.stat().st_size != meta["bytes"]:
            raise RuntimeError(f"Veröffentlichte Bytezahl für {key} stimmt nicht")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != meta["sha256"]:
            raise RuntimeError(f"Veröffentlichte SHA-256 für {key} stimmt nicht")
        validate_png(path, meta["size"])

    with Image.open(FILES["actions"]["path"]) as actions:
        actions.load()
        cells = []
        for row in range(2):
            for column in range(4):
                crop = actions.crop(
                    (column * 384, row * 512, (column + 1) * 384, (row + 1) * 512)
                )
                bbox = crop.getchannel("A").getbbox()
                if bbox is None:
                    raise RuntimeError(f"Leere Sprite-Zelle {row},{column}")
                margins = (bbox[0], bbox[1], 384 - bbox[2], 512 - bbox[3])
                if min(margins) < 20:
                    raise RuntimeError(
                        f"Sprite-Zelle {row},{column} hat zu kleinen Rand: {margins}"
                    )
                cells.append((bbox, margins))
        if cells[1][0][3] != 486 or cells[2][0][3] != 486:
            raise RuntimeError("Gehframes liegen nicht auf der gemeinsamen Bodenlinie 486")
        if actions.crop((384, 0, 768, 512)).tobytes() == actions.crop((768, 0, 1152, 512)).tobytes():
            raise RuntimeError("Die beiden Gehphasen sind identisch")

    phrase_path = SET_ROOT / "Sprüche" / "Abschiedsspruch.json"
    phrase = json.loads(phrase_path.read_text(encoding="utf-8"))
    if phrase != PHRASE or list(phrase) != ["theme", "line"] or len(phrase["line"]) > 180:
        raise RuntimeError("Abschiedsspruch.json ist ungültig")
    print("VALIDATION_OK min_sprite_margin=25 walking_baseline=486")


def publish() -> str:
    asset_paths = [
        "BeamtenMonitorAvatar/Assets 29/Avatar/Idle.png",
        "BeamtenMonitorAvatar/Assets 29/Avatar/Actions.png",
        "BeamtenMonitorAvatar/Assets 29/MonitorScene/MonitorScene.png",
        "BeamtenMonitorAvatar/Assets 29/Klingel/MonitorBell.png",
        "BeamtenMonitorAvatar/Assets 29/Sprüche/Abschiedsspruch.json",
    ]
    subprocess.check_call(["git", "config", "user.name", "Beamten Asset Automation"], cwd=ROOT)
    subprocess.check_call(["git", "config", "user.email", "actions@users.noreply.github.com"], cwd=ROOT)
    subprocess.check_call(["git", "add", "--", *asset_paths], cwd=ROOT)
    subprocess.check_call(
        ["git", "commit", "-m", "Assets 29: Kanutag Asset-Set", "--", *asset_paths],
        cwd=ROOT,
    )
    sha = run("git", "rev-parse", "HEAD")
    subprocess.check_call(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    print(f"ASSET_COMMIT={sha}")
    return sha


def post_push_verify(expected_sha: str) -> None:
    subprocess.check_call(["git", "fetch", "origin", "main"], cwd=ROOT)
    remote_sha = run("git", "rev-parse", "origin/main")
    if remote_sha != expected_sha:
        raise RuntimeError(f"origin/main ist {remote_sha}, erwartet war {expected_sha}")
    subprocess.check_call(["git", "reset", "--hard", "origin/main"], cwd=ROOT)
    validate()
    print(f"POST_PUSH_VERIFIED={remote_sha}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        validate()
        return
    reconstruct()
    validate()
    sha = publish()
    post_push_verify(sha)


if __name__ == "__main__":
    main()
