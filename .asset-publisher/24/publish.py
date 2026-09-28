from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / ".asset-publisher" / "24" / "chunks"
SET_ROOT = ROOT / "BeamtenMonitorAvatar" / "Assets 24"
THEME = "Werkstatttag"
LINE = "Ich gehe zurück in die Werkstatt – der Feierabend wurde schon maßhaltig geprüft und freigegeben."

FILES = {
    "idle": (SET_ROOT / "Avatar" / "Idle.png", (1024, 1536), 990187),
    "actions": (SET_ROOT / "Avatar" / "Actions.png", (1536, 1024), 1220371),
    "scene": (SET_ROOT / "MonitorScene" / "MonitorScene.png", (1672, 941), 1031439),
    "bell": (SET_ROOT / "Klingel" / "MonitorBell.png", (1254, 1254), 1483207),
}


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def materialize() -> None:
    if SET_ROOT.exists():
        raise RuntimeError(f"Zielordner existiert bereits: {SET_ROOT}")
    for name, (path, _, expected_size) in FILES.items():
        parts = sorted(CHUNKS.glob(f"{name}.b64.part-*"))
        if not parts:
            raise RuntimeError(f"Keine Chunks für {name}")
        encoded = "".join(p.read_text(encoding="ascii") for p in parts)
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) != expected_size:
            raise RuntimeError(f"Größe {name}: {len(raw)} != {expected_size}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    phrase = SET_ROOT / "Sprüche" / "Abschiedsspruch.json"
    phrase.parent.mkdir(parents=True, exist_ok=True)
    phrase.write_text(json.dumps({"theme": THEME, "line": LINE}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def validate_png(path: Path, expected: tuple[int, int]) -> tuple[int, int]:
    if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Ungültige PNG-Signatur: {path}")
    with Image.open(path) as probe:
        probe.verify()
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected or image.mode != "RGBA":
            raise RuntimeError(f"PNG-Metadaten falsch: {path}, {image.format}, {image.size}, {image.mode}")
        lo, hi = image.getchannel("A").getextrema()
        if lo != 0 or hi == 0:
            raise RuntimeError(f"Keine echte Transparenz: {path}, Alpha={lo, hi}")
        return lo, hi


def validate_actions(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        image.load()
        margins: list[list[int]] = []
        bboxes: list[list[int]] = []
        bottoms: list[int] = []
        for index in range(8):
            col, row = index % 4, index // 4
            crop = image.crop((col * 384, row * 512, (col + 1) * 384, (row + 1) * 512))
            bbox = crop.getchannel("A").getbbox()
            if bbox is None:
                raise RuntimeError(f"Leere Sprite-Zelle {index}")
            left, top, right, bottom = bbox
            cell_margins = [left, top, 384 - right, 512 - bottom]
            if min(cell_margins) < 20:
                raise RuntimeError(f"Sprite-Zelle {index} hat zu kleinen Rand: {cell_margins}")
            bboxes.append([left, top, right, bottom])
            margins.append(cell_margins)
            if index in (1, 2):
                bottoms.append(bottom)
        if len(set(bottoms)) != 1:
            raise RuntimeError(f"Geh-Bodenlinien unterscheiden sich: {bottoms}")
        return {"bboxes": bboxes, "margins": margins, "minMargin": min(min(x) for x in margins), "walkBaseline": bottoms[0]}


def validate_all() -> dict[str, object]:
    for _, (path, expected, expected_size) in FILES.items():
        if path.stat().st_size != expected_size:
            raise RuntimeError(f"Dateigröße verändert: {path}")
        validate_png(path, expected)
    phrase = SET_ROOT / "Sprüche" / "Abschiedsspruch.json"
    data = json.loads(phrase.read_text(encoding="utf-8"))
    if list(data) != ["theme", "line"] or data != {"theme": THEME, "line": LINE} or len(LINE) > 180:
        raise RuntimeError(f"Spruch-JSON ungültig: {data}")
    return validate_actions(FILES["actions"][0])


def main() -> None:
    materialize()
    before = validate_all()
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    paths = [str(path.relative_to(ROOT)) for path, _, _ in FILES.values()]
    paths.append(str((SET_ROOT / "Sprüche" / "Abschiedsspruch.json").relative_to(ROOT)))
    run("git", "add", "--", *paths)
    run("git", "commit", "-m", "Assets 24: Werkstatttag Asset-Set")
    asset_sha = run("git", "rev-parse", "HEAD")
    run("git", "push", "origin", "HEAD:main")
    run("git", "fetch", "origin", "main")
    run("git", "reset", "--hard", "origin/main")
    after = validate_all()
    main_sha = run("git", "rev-parse", "HEAD")
    if main_sha != asset_sha:
        raise RuntimeError(f"Post-Push-SHA weicht ab: {main_sha} != {asset_sha}")
    print(json.dumps({"assetSha": asset_sha, "mainSha": main_sha, "before": before, "after": after}, ensure_ascii=False))


if __name__ == "__main__":
    main()
