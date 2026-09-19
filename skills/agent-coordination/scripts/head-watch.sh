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
# Notes:
#   - Commit-landing detector only. File-only completion without a commit
#     is invisible here; pair with sentinel-wait.sh for that case.
#   - Interval default is 10s (old 120s missed short tasks by minutes).
set -euo pipefail

repo="${1:-.}"
interval="${2:-10}"
timeout_sec="${3:-28800}"

if ! git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
  echo "NOT-A-REPO repo=$repo" >&2
  exit 2
fi
start="$(git -C "$repo" rev-parse HEAD 2>/dev/null || echo UNBORN)"
end=$((SECONDS + timeout_sec))
while [ "$SECONDS" -lt "$end" ]; do
  sleep "$interval"
  cur="$(git -C "$repo" rev-parse HEAD 2>/dev/null || echo UNBORN)"
  if [ "$cur" != "$start" ]; then
    echo "HEAD-CHANGED old=$start new=$cur"
    if [ "$start" = "UNBORN" ]; then
      git -C "$repo" log --oneline -5
    else
      git -C "$repo" log --oneline "$start..$cur"
    fi
    exit 0
  fi
done
echo "WATCH-TIMEOUT no new commits"
exit 2
