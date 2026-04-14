#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRACE_FILE="${1:-/tmp/endcord-vim-cursor-trace.jsonl}"
RAW_FILE="${2:-/tmp/endcord-vim-cursor.raw}"
PROMPT="${ENDCORD_CURSOR_PROMPT:-[Paramount] > }"

rm -f "$TRACE_FILE" "$RAW_FILE"
cd "$ROOT"
ENDCORD_CURSOR_TRACE="$TRACE_FILE" TERM=xterm-256color script -qfc "PYTHONPATH=. uv run python tools/vim_cursor_probe.py --trace-file '$TRACE_FILE' --prompt '$PROMPT'" "$RAW_FILE"
PYTHONPATH=. uv run python tools/analyze_cursor_trace.py "$TRACE_FILE"
echo "trace: $TRACE_FILE"
echo "raw:   $RAW_FILE"
