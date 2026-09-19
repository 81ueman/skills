#!/usr/bin/env bash
# Watch a git repo for new commits and report when HEAD moves.
#
# Coordinator agents in this workflow record verification milestones as
# commits (e.g. timeline updates). Polling HEAD is the cheapest reliable
# "something landed" detector: it fires rarely and says exactly what landed.
#
# Usage:
#   head-watch.sh [repo_dir] [interval_sec] [timeout_sec]
#
# Exit codes: 0 = HEAD changed (prints old/new + log), 2 = timeout.
set -euo pipefail

repo="${1:-.}"
interval="${2:-120}"
timeout_sec="${3:-28800}"

start="$(git -C "$repo" rev-parse HEAD)"
end=$((SECONDS + timeout_sec))
while [ "$SECONDS" -lt "$end" ]; do
  sleep "$interval"
  cur="$(git -C "$repo" rev-parse HEAD)"
  if [ "$cur" != "$start" ]; then
    echo "HEAD-CHANGED old=$start new=$cur"
    git -C "$repo" log --oneline "$start..$cur"
    exit 0
  fi
done
echo "WATCH-TIMEOUT no new commits"
exit 2
