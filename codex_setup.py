"""Install / remove the read-aloud Stop hook for OpenAI Codex (CLI and app).

Codex reads hooks from ~/.codex/hooks.json using the same shape as Claude Code, and passes
`last_assistant_message` to Stop hooks. New hooks must be approved once inside Codex
("Hooks need review" -> Trust); this installer never bypasses that review.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MARKER = "read-aloud"
HOOK_TIMEOUT_S = 15


def hooks_path() -> Path:
    return Path.home() / ".codex" / "hooks.json"


def hook_command(script: Path) -> str:
    return f'"{sys.executable}" "{script}" hook'


def _is_ours(handler: dict) -> bool:
    return MARKER in str(handler.get("command", "")) and "speak.py" in str(handler.get("command", ""))


def without_ours(config: dict) -> dict:
    """Return a copy of the hooks config with every read-aloud Stop handler removed."""
    hooks = dict(config.get("hooks", {}))
    groups = []
    for group in hooks.get("Stop", []):
        kept = [h for h in group.get("hooks", []) if not _is_ours(h)]
        if kept:
            groups.append({**group, "hooks": kept})
    if groups:
        hooks["Stop"] = groups
    else:
        hooks.pop("Stop", None)
    return {**config, "hooks": hooks}


def with_ours(config: dict, command: str) -> dict:
    clean = without_ours(config)
    hooks = dict(clean["hooks"])
    handler = {"type": "command", "command": command, "timeout": HOOK_TIMEOUT_S}
    hooks["Stop"] = [*hooks.get("Stop", []), {"hooks": [handler]}]
    return {**clean, "hooks": hooks}


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install(script: Path) -> None:
    path = hooks_path()
    _save(path, with_ours(_load(path), hook_command(script)))
    print(f"read-aloud: Codex hook added to {path}")
    print("Next: open Codex. When it says 'Hooks need review', review the hook and choose Trust.")


def uninstall() -> None:
    path = hooks_path()
    if not path.exists():
        print("read-aloud: no Codex hooks file, nothing to remove")
        return
    _save(path, without_ours(_load(path)))
    print(f"read-aloud: Codex hook removed from {path}")
