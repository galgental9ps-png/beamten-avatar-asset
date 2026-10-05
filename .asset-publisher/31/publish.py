from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[2]
SET = ROOT / "BeamtenMonitorAvatar" / "Assets 31"
SOURCE = ROOT / ".asset-publisher" / "31" / "chunks"
FILES = {
    "Idle": {
        "target": SET / "Avatar" / "Idle.png",
        "size": (1024, 1536),
        "bytes": 1063861,
        "sha256": "7fb7a98cc576ba8624a63be9729cc063eddc52a313e742019c5826703120d365",
    },
    "Actions": {
        "target": SET / "Avatar" / "Actions.png",
        "size": (1536, 1024),
        "bytes": 1368494,
        "sha256": "b9c1e7ed86a31f000cbb42db826531fa90adb218bb97b40d6f3e369fed106adf",
    },
    "MonitorScene": {
        "target": SET / "MonitorScene" / "MonitorScene.png",
        "size": (1672, 941),
        "bytes": 1384683,
        "sha256": "23d09ee71f0f9679f34d3ae5813487806ef1f0f5f5d2435934486572d27916a7",
    },
    "MonitorBell": {
        "target": SET / "Klingel" / "MonitorBell.png",
        "size": (1254, 1254),
        "bytes": 1465034,
        "sha256": "379f89c99f374df90d9166d4ed655c771a734bf4a9a07e0ca1a163f57e31d9aa",
    },
}
PHRASE = {
    "theme": "Apfeltag",
    "line": "Ich bringe die Äpfel ins Lager – die Ernteakte ist bereits abgeheftet.",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def reconstruct() -> None:
    for name, item in FILES.items():
        encoded = "".join(
            path.read_text(encoding="ascii")
            for path in sorted(SOURCE.glob(f"{name}.*.b64"))
        )
        if not encoded:
            raise RuntimeError(f"Keine Datenblöcke für {name}")
        data = base64.b64decode(encoded, validate=True)
        if len(data) != item["bytes"]:
            raise RuntimeError(f"Dateigröße stimmt nicht: {name}")
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise RuntimeError(f"SHA-256 stimmt nicht: {name}")
        target = item["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    phrase_path = SET / "Sprüche" / "Abschiedsspruch.json"
    phrase_path.parent.mkdir(parents=True, exist_ok=True)
    phrase_path.write_text(
        json.dumps(PHRASE, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def verify_png(path: Path, expected_size: tuple[int, int]) -> Image.Image:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Keine PNG-Signatur: {path}")
    with Image.open(path) as check:
        check.verify()
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected_size or image.mode != "RGBA":
            raise RuntimeError(f"Ungültiges PNG: {path}")
        if image.getchannel("A").getextrema()[0] != 0:
            raise RuntimeError(f"Keine echte Transparenz: {path}")
        return image.copy()


def verify() -> None:
    opened = {
        name: verify_png(item["target"], item["size"])
        for name, item in FILES.items()
    }
    actions = opened["Actions"]
    cells = []
    for row in range(2):
        for col in range(4):
            crop = actions.crop((col * 384, row * 512, (col + 1) * 384, (row + 1) * 512))
            box = crop.getchannel("A").getbbox()
            if box is None:
                raise RuntimeError(f"Leere Sprite-Zelle {row},{col}")
            margins = (box[0], box[1], 384 - box[2], 512 - box[3])
            if min(margins) < 20:
                raise RuntimeError(f"Zu kleiner Rand in Sprite-Zelle {row},{col}: {margins}")
            cells.append((box, margins))
    if cells[1][0][3] != 486 or cells[2][0][3] != 486:
        raise RuntimeError("Gehphasen haben nicht dieselbe Bodenlinie")
    walk1 = actions.crop((384, 0, 768, 512)).getchannel("A")
    walk2 = actions.crop((768, 0, 1152, 512)).getchannel("A")
    if ImageChops.difference(walk1, walk2).getbbox() is None:
        raise RuntimeError("Gehphasen sind identisch")
    phrase_path = SET / "Sprüche" / "Abschiedsspruch.json"
    phrase = json.loads(phrase_path.read_text(encoding="utf-8"))
    if list(phrase) != ["theme", "line"] or phrase != PHRASE or len(phrase["line"]) > 180:
        raise RuntimeError("Ungültige Spruchdatei")


def publish() -> str:
    paths = [str(item["target"].relative_to(ROOT)) for item in FILES.values()]
    paths.append(str((SET / "Sprüche" / "Abschiedsspruch.json").relative_to(ROOT)))
    subprocess.check_call(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT)
    subprocess.check_call(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT)
    subprocess.check_call(["git", "add", "--", *paths], cwd=ROOT)
    subprocess.check_call(["git", "commit", "-m", "Assets 31: Apfeltag Asset-Set", "--", *paths], cwd=ROOT)
    asset_sha = run("git", "rev-parse", "HEAD")
    subprocess.check_call(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    subprocess.check_call(["git", "fetch", "origin", "main"], cwd=ROOT)
    origin_sha = run("git", "rev-parse", "origin/main")
    if origin_sha != asset_sha:
        raise RuntimeError(f"origin/main {origin_sha} entspricht nicht Asset-Commit {asset_sha}")
    subprocess.check_call(["git", "reset", "--hard", "origin/main"], cwd=ROOT)
    verify()
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"asset_sha={asset_sha}\n")
    print(f"ASSET_SHA={asset_sha}")
    return asset_sha


if __name__ == "__main__":
    reconstruct()
    verify()
    publish()
