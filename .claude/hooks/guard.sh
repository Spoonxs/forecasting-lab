#!/usr/bin/env bash
# PreToolUse(Bash): block a shell command that looks like it carries a secret
# (webhook URL, PEM private key, or an API_KEY/SECRET/TOKEN assignment).
# Exit 2 blocks the tool call and tells Claude why. Hook input is JSON on stdin:
# {"tool_input": {"command": "..."}}.

c=$(python -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
if printf '%s' "$c" | grep -Eq 'DISCORD_WEBHOOK|discord\.com/api/webhooks|-----BEGIN|(API_KEY|SECRET|TOKEN)='; then
  echo "guard hook: command looks like it contains a secret — blocked. Put secrets in .env, not the command line." >&2
  exit 2
fi
exit 0
