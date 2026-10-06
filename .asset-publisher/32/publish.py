from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[2]
SET = ROOT / "BeamtenMonitorAvatar" / "Assets 32"
SOURCE = ROOT / ".asset-publisher" / "32" / "chunks"
FILES = {
    "Idle": {
        "target": SET / "Avatar" / "Idle.png",
        "size": (1024, 1536),
        "bytes": 928778,
        "sha256": "8a48884902f00dbd7778ce6afb015f2dffb5bbd474ede120e09d8104b8d851fe",
    },
    "Actions": {
        "target": SET / "Avatar" / "Actions.png",
        "size": (1536, 1024),
        "bytes": 1296906,
        "sha256": "e390692791808ea0504c8a2a8587aa1e036bf1a24e5d5eb14cb2b93297d69ac1",
    },
    "MonitorScene": {
        "target": SET / "MonitorScene" / "MonitorScene.png",
        "size": (1672, 941),
        "bytes": 1142491,
        "sha256": "82982f8373931d0030706397e69857fbcaeafad2405b267794d6a156e589185f",
    },
    "MonitorBell": {
        "target": SET / "Klingel" / "MonitorBell.png",
        "size": (1254, 1254),
        "bytes": 1544762,
        "sha256": "799222a142edcc32b6af9347f9f8c655128ea56da05644e064847485583ca4ea",
    },
}
PHRASE = {
    "theme": "Uhrmachertag",
    "line": "Ich stelle die Uhr zurück – der Feierabend ist fristgerecht eingetaktet.",
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
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected_size or image.mode != "RGBA":
            raise RuntimeError(f"Ungültiges PNG: {path}")
        minimum, maximum = image.getchannel("A").getextrema()
        if minimum != 0 or maximum <= 0:
            raise RuntimeError(f"Keine echte Transparenz: {path}")
        return image.copy()


def verify() -> None:
    opened = {
        name: verify_png(item["target"], item["size"])
        for name, item in FILES.items()
    }
    actions = opened["Actions"]
    boxes = []
    for row in range(2):
        for col in range(4):
            crop = actions.crop((col * 384, row * 512, (col + 1) * 384, (row + 1) * 512))
            box = crop.getchannel("A").getbbox()
            if box is None:
                raise RuntimeError(f"Leere Sprite-Zelle {row},{col}")
            margins = (box[0], box[1], 384 - box[2], 512 - box[3])
            if min(margins) < 20:
                raise RuntimeError(f"Zu kleiner Rand in Sprite-Zelle {row},{col}: {margins}")
            boxes.append(box)
    if boxes[1][3] != 486 or boxes[2][3] != 486:
        raise RuntimeError("Gehphasen haben nicht dieselbe Bodenlinie")
    walk1 = actions.crop((384, 0, 768, 512)).getchannel("A")
    walk2 = actions.crop((768, 0, 1152, 512)).getchannel("A")
    if ImageChops.difference(walk1, walk2).getbbox() is None:
        raise RuntimeError("Gehphasen sind identisch")
    if abs((boxes[1][2] - boxes[1][0]) - (boxes[2][2] - boxes[2][0])) < 35:
        raise RuntimeError("Gehphasen unterscheiden sich nicht deutlich genug")
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
    subprocess.check_call(["git", "commit", "-m", "Assets 32: Uhrmachertag Asset-Set", "--", *paths], cwd=ROOT)
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
