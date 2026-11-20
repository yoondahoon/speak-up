#!/usr/bin/env python3
"""read-aloud: read Claude Code's final reply aloud, in any language, with free TTS.

Usage:
  speak.py hook            Called by the Claude Code Stop hook (reads JSON on stdin)
  speak.py on | off        Enable / disable reading aloud
  speak.py stop            Stop the current speech
  speak.py status          Show current settings
  speak.py say "text"      Speak arbitrary text (for testing)
  speak.py voices          List installed system voices

Engines (READ_ALOUD_ENGINE): auto (default), sapi (Windows), say (macOS),
espeak (Linux), edge (optional, needs `pip install edge-tts`, online).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang as langdetect  # noqa: E402

ROOT = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".claude" / "read-aloud"
OFF_FLAG = STATE_DIR / "off"
PID_FILE = STATE_DIR / "speaking.pid"

DEFAULT_MAX_CHARS = 1200
TRANSCRIPT_RETRIES = 3
TRANSCRIPT_RETRY_DELAY_S = 0.3
IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"



def env(name: str, default: str = "") -> str:
    return os.environ.get(f"READ_ALOUD_{name}", default).strip()


# ---------------------------------------------------------------- text cleanup

_EMOJI = re.compile("[🀀-🫿☀-➿⬀-⯿️‍]")


def clean_markdown(text: str) -> str:
    """Turn a markdown reply into plain sentences that sound natural when spoken."""
    text = _EMOJI.sub("", text)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)           # code blocks
    text = re.sub(r"`([^`]*)`", r"\1", text)                      # inline code
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)              # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)           # links -> label
    text = re.sub(r"https?://\S+", " ", text)                      # bare urls
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?", stripped):
            continue                                               # table separator
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            stripped = ", ".join(c for c in cells if c)
        stripped = re.sub(r"^#{1,6}\s*", "", stripped)              # headings
        stripped = re.sub(r"^>\s?", "", stripped)                   # quotes
        stripped = re.sub(r"^([-*+]|\d+[.)])\s+", "", stripped)     # list markers
        if re.fullmatch(r"[-*_]{3,}", stripped):
            continue                                               # horizontal rule
        if stripped:
            if not re.search(r"[.!?。！？:]$", stripped):
                stripped += "."
            lines.append(stripped)
    text = " ".join(lines)
    text = re.sub(r"(\*\*|__|\*|_|~~)(.+?)\1", r"\2", text)        # bold/italic/strike
    text = text.replace("→", ", ").replace("←", ", ")
    text = re.sub(r"[*#|<>]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > max_chars // 3 else cut


def detect_lang(text: str) -> str:
    hint = env("LANG") or langdetect.claude_language_setting()
    return langdetect.detect_lang(text, hint)


# ------------------------------------------------------------ reading the reply

def _text_of(entry: dict) -> str:
    content = entry.get("message", {}).get("content", [])
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", "") for c in content
                     if isinstance(c, dict) and c.get("type") == "text")


def last_reply_from_transcript(path: str) -> str:
    """Collect assistant text written after the most recent user/tool entry."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return ""
    parts: list[str] = []
    for raw in reversed(raw_lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        kind = entry.get("type")
        if kind == "user":
            break
        if kind == "assistant" and not entry.get("isSidechain"):
            text = _text_of(entry)
            if text.strip():
                parts.append(text)
    return "\n".join(reversed(parts))


def reply_from_hook_input(data: dict) -> str:
    direct = data.get("last_assistant_message")
    if isinstance(direct, str) and direct.strip():
        return direct
    path = data.get("transcript_path")
    if not path:
        return ""
    for _ in range(TRANSCRIPT_RETRIES):          # transcript may still be flushing
        reply = last_reply_from_transcript(path)
        if reply:
            return reply
        time.sleep(TRANSCRIPT_RETRY_DELAY_S)
    return ""


# --------------------------------------------------------------------- engines

def pick_engine() -> str:
    choice = env("ENGINE", "auto").lower()
    if choice != "auto":
        return choice
    if IS_WINDOWS:
        return "sapi"
    if IS_MAC:
        return "say"
    return "espeak"


def build_command(engine: str, text_file: Path, lang: str) -> list[str]:
    short = langdetect.base(lang)
    voice = env(f"VOICE_{short.upper()}") or env("VOICE")   # e.g. READ_ALOUD_VOICE_KO
    rate = env("RATE", "0")
    if engine == "sapi":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "engines" / "sapi.ps1"), "-TextFile", str(text_file),
                "-Lang", lang, "-Rate", rate, "-Voice", voice]
    if engine == "say":
        voice = voice or mac_voice(lang)
        cmd = ["say", "-f", str(text_file)] + (["-v", voice] if voice else [])
        return cmd + (["-r", rate] if rate not in ("", "0") else [])
    if engine == "espeak":
        exe = shutil.which("espeak-ng") or shutil.which("espeak") or "espeak-ng"
        return [exe, "-v", voice or lang.lower(), "-f", str(text_file)]
    if engine == "edge":
        return [sys.executable, str(ROOT / "engines" / "edge.py"), str(text_file),
                voice or f"auto:{lang}", rate]
    raise ValueError(f"unknown engine: {engine}")


def mac_voice(lang: str) -> str:
    """Pick an installed macOS voice whose locale matches, e.g. 'ko' -> 'Yuna'."""
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True,
                             timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    want = lang.replace("-", "_").lower()
    matches = []
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s{2,}([a-z]{2,3}_[A-Z0-9]{2,3})\s", line)
        if m:
            matches.append((m.group(1).strip(), m.group(2).lower()))
    for name, loc in matches:
        if loc == want:
            return name
    for name, loc in matches:
        if loc.split("_")[0] == langdetect.base(lang):
            return name
    return ""


def stop_speaking() -> None:
    try:
        pid = int(PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    PID_FILE.unlink(missing_ok=True)


def speak(text: str) -> None:
    text = truncate(clean_markdown(text), int(env("MAX_CHARS", str(DEFAULT_MAX_CHARS))))
    if not text:
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stop_speaking()
    fd, name = tempfile.mkstemp(prefix="read-aloud-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    cmd = build_command(pick_engine(), Path(name), detect_lang(text))
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL, "close_fds": True}
    if IS_WINDOWS:
        kwargs["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP
                                   | subprocess.CREATE_NO_WINDOW)
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)        # detached: never blocks Claude Code
    PID_FILE.write_text(str(proc.pid))


# ------------------------------------------------------------------------- cli

def run_hook() -> None:
    if OFF_FLAG.exists():
        return
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw or "{}")
    except ValueError:
        return
    if data.get("stop_hook_active"):
        return
    reply = reply_from_hook_input(data)
    if reply:
        speak(reply)


def list_voices() -> None:
    engine = pick_engine()
    if engine == "sapi":
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Add-Type -AssemblyName System.Speech;"
                        "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
                        ".GetInstalledVoices() | % { $_.VoiceInfo.Name + ' | ' +"
                        " $_.VoiceInfo.Culture }"])
    elif engine == "say":
        subprocess.run(["say", "-v", "?"])
    elif engine == "edge":
        subprocess.run([sys.executable, "-m", "edge_tts", "--list-voices"])
    else:
        subprocess.run([build_command("espeak", Path("x"), "en")[0], "--voices"])


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "hook":
        try:
            run_hook()
        except Exception as exc:  # a TTS failure must never break Claude Code
            print(f"read-aloud: {exc}", file=sys.stderr)
        return 0
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if cmd == "on":
        OFF_FLAG.unlink(missing_ok=True)
        print("read-aloud: ON")
    elif cmd == "off":
        OFF_FLAG.touch()
        stop_speaking()
        print("read-aloud: OFF")
    elif cmd == "stop":
        stop_speaking()
        print("read-aloud: stopped")
    elif cmd == "say":
        speak(" ".join(argv[2:]) or "Hello from read aloud.")
    elif cmd == "voices":
        list_voices()
    elif cmd == "status":
        print(f"read-aloud: {'OFF' if OFF_FLAG.exists() else 'ON'} | "
              f"engine={pick_engine()} voice={env('VOICE') or 'auto'} "
              f"rate={env('RATE', '0')} max_chars={env('MAX_CHARS', str(DEFAULT_MAX_CHARS))}")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
