#!/usr/bin/env bash
cd "$(dirname "$0")/.."
for f in .run/*.pid; do [ -f "$f" ] || continue; kill "$(cat "$f")" 2>/dev/null && echo "đã dừng $(basename "$f" .pid)"; rm -f "$f"; done
