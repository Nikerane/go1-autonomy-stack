#!/usr/bin/env bash
# deploy.sh — rsync this repo to both robot boards.
#
# After running this, the repo is available at ~/go1-autonomy-stack/ on both
# .14 (Nano 4GB, ROS master) and .15 (Xavier NX, OAK-D).
#
# Usage:
#   ./scripts/deploy.sh            # push to both boards
#   ./scripts/deploy.sh .14        # only Nano
#   ./scripts/deploy.sh .15        # only Xavier
#
# Run from the repo root.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-both}"

PASS="123"
REMOTE="go1-autonomy-stack/"

push() {
  local host="$1"
  echo "[deploy] Pushing to $host:~/$REMOTE"
  sshpass -p "$PASS" rsync -az --delete \
    --exclude '.git/' \
    --exclude 'build/' \
    --exclude 'devel/' \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    "$REPO_ROOT/" "unitree@$host:~/$REMOTE"
}

case "$TARGET" in
  both|"")
    push 192.168.123.14
    push 192.168.123.15
    ;;
  .14|14|nano)
    push 192.168.123.14
    ;;
  .15|15|xavier|nx)
    push 192.168.123.15
    ;;
  *)
    echo "Unknown target: $TARGET" >&2
    exit 1
    ;;
esac

echo "[deploy] Done."
