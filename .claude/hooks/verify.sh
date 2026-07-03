#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit): after a Python edit, run ruff + pytest.
# Exit 2 (with output on stderr) blocks and feeds the failure back to Claude so it
# can't drift past a red suite. Non-.py edits (docs, json) skip fast.
# Hook input is JSON on stdin: {"tool_input": {"file_path": "..."}}.

f=$(python -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
case "$f" in
  *.py) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
out=$(python -m ruff check src tests --quiet 2>&1 && python -m pytest -q -p no:warnings --tb=line 2>&1)
if [ $? -ne 0 ]; then
  echo "$out" >&2
  echo "verify hook: ruff/pytest failed after editing $f — fix before continuing." >&2
  exit 2
fi
exit 0
