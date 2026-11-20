"""Optional neural voices via the `edge-tts` package (online, no API key).

Note: edge-tts talks to Microsoft Edge's Read Aloud service. It is free but not an
official public API, so it may change or stop working. The default engines are
fully offline and use only the operating system's own voices.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = Path.home() / ".claude" / "read-aloud" / "edge-voices.json"
CACHE_MAX_AGE_S = 7 * 24 * 3600
# Preferred region when a language is spoken in many places.
DEFAULT_REGION = {
    "en": "US", "es": "ES", "pt": "BR", "zh": "CN", "ar": "SA", "fr": "FR", "de": "DE",
    "it": "IT", "nl": "NL", "ru": "RU", "sw": "KE", "ta": "IN", "ur": "PK", "bn": "IN",
    "ms": "MY", "ko": "KR", "ja": "JP", "hi": "IN", "fil": "PH", "tl": "PH",
}
FALLBACK_VOICE = "en-US-AriaNeural"


def list_voices() -> list[dict]:
    try:
        if time.time() - CACHE.stat().st_mtime < CACHE_MAX_AGE_S:
            return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    import edge_tts  # noqa: PLC0415
    import asyncio  # noqa: PLC0415

    voices = asyncio.run(edge_tts.list_voices())
    slim = [{"ShortName": v["ShortName"], "Locale": v["Locale"]} for v in voices]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(slim), encoding="utf-8")
    return slim


def resolve_voice(spec: str) -> str:
    """'auto:pt-BR' -> a pt-BR voice name. A full voice name is returned as is."""
    if not spec.startswith("auto:"):
        return spec
    lang = spec[5:]
    short = lang.split("-")[0].lower()
    alias = {"tl": "fil", "nb": "nb", "yue": "zh-HK"}.get(short)
    if alias and "-" in alias:
        lang, short = alias, alias.split("-")[0]
    elif alias:
        short = alias
    try:
        voices = list_voices()
    except Exception:  # offline: let synthesis fail and fall back
        return FALLBACK_VOICE
    wanted = lang if "-" in lang else f"{short}-{DEFAULT_REGION.get(short, '')}"
    # Single-language voices first: they sound most native.
    voices = sorted(voices, key=lambda v: "Multilingual" in v["ShortName"])
    for loc in (wanted, None):
        for v in voices:
            locale = v["Locale"]
            if (loc and locale.lower() == loc.lower()) or (
                    not loc and locale.split("-")[0].lower() == short):
                return v["ShortName"]
    return FALLBACK_VOICE


def play(mp3: Path) -> None:
    if os.name == "nt":
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(ROOT / "play.ps1"), "-File", str(mp3)])
    elif sys.platform == "darwin":
        subprocess.run(["afplay", str(mp3)])
    else:
        player = shutil.which("mpg123") or shutil.which("ffplay")
        if not player:
            raise SystemExit("edge engine on Linux needs mpg123 or ffplay")
        extra = ["-nodisp", "-autoexit", "-loglevel", "quiet"] if "ffplay" in player else ["-q"]
        subprocess.run([player, *extra, str(mp3)])


def offline_fallback(text_file: Path, voice: str, rate: int) -> None:
    """Speak with the OS voice when edge-tts is missing or offline."""
    lang = voice[5:] if voice.startswith("auto:") else "-".join(voice.split("-")[:2])
    lang = lang or "en"
    if os.name == "nt":
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "sapi.ps1"), "-TextFile", str(text_file),
                        "-Lang", lang, "-Rate", str(rate)])
    elif sys.platform == "darwin":
        subprocess.run(["say", "-f", str(text_file)])
    else:
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        if exe:
            subprocess.run([exe, "-v", lang, "-f", str(text_file)])


def main() -> None:
    text_file, spec = Path(sys.argv[1]), sys.argv[2]
    rate = int(sys.argv[3] or 0) if len(sys.argv) > 3 else 0
    voice = spec
    fd, name = tempfile.mkstemp(prefix="read-aloud-", suffix=".mp3")
    os.close(fd)
    mp3 = Path(name)
    try:
        try:
            import edge_tts  # noqa: PLC0415

            voice = resolve_voice(spec)
            text = text_file.read_text(encoding="utf-8")
            # SAPI-style rate (-10..10) mapped to edge's percentage (+/-100%)
            edge_tts.Communicate(text, voice, rate=f"{rate * 10:+d}%").save_sync(str(mp3))
        except Exception as exc:  # missing package, offline, service change
            print(f"read-aloud: edge failed ({exc}); using system voice", file=sys.stderr)
            offline_fallback(text_file, voice, rate)
            return
        play(mp3)
    finally:
        text_file.unlink(missing_ok=True)
        mp3.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
