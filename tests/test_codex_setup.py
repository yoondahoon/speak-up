import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_setup  # noqa: E402

CMD = '"python" "/x/read-aloud/speak.py" hook'
OTHER = {"type": "command", "command": "notify-me"}


class CodexSetupTest(unittest.TestCase):
    def test_adds_hook_to_empty_config(self) -> None:
        out = codex_setup.with_ours({}, CMD)
        self.assertEqual(out["hooks"]["Stop"][0]["hooks"][0]["command"], CMD)

    def test_keeps_other_hooks_and_settings(self) -> None:
        config = {"x": 1, "hooks": {"Stop": [{"hooks": [OTHER]}], "PreToolUse": [{"hooks": [OTHER]}]}}
        out = codex_setup.with_ours(config, CMD)
        self.assertEqual(out["x"], 1)
        self.assertEqual(out["hooks"]["PreToolUse"], config["hooks"]["PreToolUse"])
        self.assertEqual(out["hooks"]["Stop"][0]["hooks"], [OTHER])
        self.assertEqual(len(out["hooks"]["Stop"]), 2)

    def test_install_twice_does_not_duplicate(self) -> None:
        once = codex_setup.with_ours({}, CMD)
        twice = codex_setup.with_ours(once, CMD)
        self.assertEqual(once, twice)

    def test_uninstall_removes_only_ours(self) -> None:
        config = codex_setup.with_ours({"hooks": {"Stop": [{"hooks": [OTHER]}]}}, CMD)
        out = codex_setup.without_ours(config)
        self.assertEqual(out["hooks"]["Stop"], [{"hooks": [OTHER]}])
        self.assertEqual(codex_setup.without_ours(codex_setup.with_ours({}, CMD))["hooks"], {})

    def test_does_not_mutate_input(self) -> None:
        config = {"hooks": {"Stop": [{"hooks": [OTHER]}]}}
        codex_setup.with_ours(config, CMD)
        self.assertEqual(config, {"hooks": {"Stop": [{"hooks": [OTHER]}]}})


if __name__ == "__main__":
    unittest.main()
