#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
candidate_root=${1:?Usage: scripts/prepare-release-candidate.sh /absolute/candidate-directory}

case "$candidate_root" in
  /*) ;;
  *) printf '%s\n' 'candidate directory must be absolute' >&2; exit 64 ;;
esac

if [ -e "$candidate_root" ]; then
  printf '%s\n' 'candidate directory must not already exist' >&2
  exit 64
fi

git -C "$root" diff --quiet && git -C "$root" diff --cached --quiet || {
  printf '%s\n' 'repository has uncommitted changes; prepare a clean revision first' >&2
  exit 1
}

git -C "$root" ls-files -ci --exclude-standard | grep . >/dev/null && {
  printf '%s\n' 'repository contains unresolved case-collision paths' >&2
  exit 1
}

if [ -n "${TRAFFIC_SIM_PYTHON:-}" ]; then
  release_python=$TRAFFIC_SIM_PYTHON
elif [ -x "$root/.venv/bin/python" ]; then
  release_python=$root/.venv/bin/python
else
  release_python=python3
fi

git clone --no-local --no-tags "$root" "$candidate_root"
git -C "$candidate_root" checkout --detach HEAD
PYTHONPATH="$candidate_root/src" "$release_python" "$candidate_root/scripts/bootstrap_portfolio.py" \
  --repository-root "$candidate_root" \
  --run-id "abay-candidate-${SOURCE_DATE_EPOCH:-0}"
printf '%s\n' "$candidate_root"
