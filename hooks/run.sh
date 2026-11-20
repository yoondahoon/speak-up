#!/usr/bin/env bash
# Finds a working Python 3 (python3 on macOS/Linux, python or py on Windows).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for exe in python3 python py; do
  if "$exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
    exec "$exe" "$DIR/speak.py" "$@"
  fi
done
echo "read-aloud: Python 3.9+ not found" >&2
exit 0
