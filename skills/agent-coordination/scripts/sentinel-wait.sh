#!/usr/bin/env bash
# Wait for a sentinel DONE file to appear and be non-empty.
#
# Subordinate agents record completion as a file (not just pane text)
# so the parent can detect it without matching its own echo.
# Use a UUID-suffixed path to avoid matching stale files.
#
# Usage:
#   sentinel-wait.sh <file> [timeout_sec] [interval_sec]
#
# Exit codes: 0 = found (prints SENTINEL-FOUND + content), 2 = timeout.
set -euo pipefail

file="${1:?usage: sentinel-wait.sh <file> [timeout_sec] [interval_sec]}"
timeout_sec="${2:-3600}"
interval="${3:-2}"

if [ -s "$file" ]; then
  echo "SENTINEL-FOUND file=$file (pre-existing)"
  cat "$file"
  exit 0
fi

end=$((SECONDS + timeout_sec))
while [ "$SECONDS" -lt "$end" ]; do
  sleep "$interval"
  if [ -s "$file" ]; then
    echo "SENTINEL-FOUND file=$file"
    cat "$file"
    exit 0
  fi
done
echo "SENTINEL-TIMEOUT file=$file timeout=${timeout_sec}s"
exit 2
