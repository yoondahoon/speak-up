"""Optional neural voices via the `edge-tts` package (online, no API key).

Note: edge-tts talks to Microsoft Edge's Read Aloud service. It is free but not an
official public API, so it may change or stop working. The default engines are
fully offline and use only the operating system's own voices.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


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
    lang = voice.split("-")[0] if voice else "en"
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
    text_file, voice = Path(sys.argv[1]), sys.argv[2]
    rate = int(sys.argv[3] or 0) if len(sys.argv) > 3 else 0
    fd, name = tempfile.mkstemp(prefix="read-aloud-", suffix=".mp3")
    os.close(fd)
    mp3 = Path(name)
    try:
        try:
            import edge_tts  # noqa: PLC0415

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
