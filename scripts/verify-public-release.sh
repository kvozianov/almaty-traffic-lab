#!/usr/bin/env sh
set -eu

stage=""
tag=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --stage) stage="${2:-}"; shift 2 ;;
    --tag) tag="${2:-}"; shift 2 ;;
    --help|-h)
      printf '%s\n' 'Usage: npm run verify:release -- --stage candidate|tagged [--tag vX.Y.Z]'
      exit 0
      ;;
    *) printf '%s\n' "verify:release: unsupported argument: $1" >&2; exit 64 ;;
  esac
done

case "$stage" in candidate|tagged) ;; *) printf '%s\n' 'verify:release: --stage candidate|tagged is required' >&2; exit 64 ;; esac
[ "$stage" != tagged ] || [ -n "$tag" ] || { printf '%s\n' 'verify:release: --tag is required for tagged stage' >&2; exit 64; }
[ "$stage" != candidate ] || [ -z "$tag" ] || { printf '%s\n' 'verify:release: --tag is only valid for tagged stage' >&2; exit 64; }

git diff --quiet && git diff --cached --quiet || { printf '%s\n' 'verify:release: worktree/index must be clean' >&2; exit 1; }
if git ls-files -ci --exclude-standard | grep -q .; then
  printf '%s\n' 'verify:release: tracked ignored files found' >&2
  exit 1
fi
[ "$stage" != tagged ] || git rev-parse -q --verify "refs/tags/$tag" >/dev/null || { printf '%s\n' "verify:release: missing tag $tag" >&2; exit 1; }

npm run portfolio:bootstrap -- --verify-current
npm run portfolio:bootstrap -- --verify-sources
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
PYTHONPATH=src .venv/bin/python scripts/verify_portfolio_determinism.py --repository-root .
npm run lint
npx tsc --noEmit --pretty false --incremental false
npm run build
node tests/english_ui_contract.mjs
node tests/portfolio_download_contract.mjs
node tests/docs_contract.mjs
sh scripts/verify-public-routes.sh
npm audit --omit=dev --audit-level=high
printf '%s\n' "verify:release: $stage checks passed"
