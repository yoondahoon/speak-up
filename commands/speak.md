---
description: Turn reading-aloud on/off, stop speech, or show status (on | off | stop | status | voices)
argument-hint: on | off | stop | status | voices
allowed-tools: Bash(bash:*)
---

Run this command and report its output to the user in one short line:

```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" $ARGUMENTS
```

If no argument was given, use `status`.
