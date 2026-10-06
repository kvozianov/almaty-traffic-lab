#!/usr/bin/env sh
set -eu

node tests/trip_trail_animation.mjs

port=${PORTFOLIO_TEST_PORT:-3036}
qa_root=$(mktemp -d "${TMPDIR:-/tmp}/portfolio-route-qa.XXXXXX")
server_log=$qa_root/server.log

cleanup() {
  if [ -n "${server_pid:-}" ]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

PORT="$port" HOSTNAME=127.0.0.1 npm run start >"$server_log" 2>&1 &
server_pid=$!

attempt=0
until node -e "fetch('http://127.0.0.1:$port/api/dossier').then((response) => process.exit(response.ok ? 0 : 1)).catch(() => process.exit(1))"; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    cat "$server_log" >&2
    printf '%s\n' 'public-route verification: server did not become healthy' >&2
    exit 1
  fi
  sleep 1
done

PORTFOLIO_URL="http://127.0.0.1:$port" \
  PORTFOLIO_HEADLESS=true \
  PORTFOLIO_QA_OUTPUT_DIR="$qa_root" \
  node tests/portfolio_m3_quality.mjs

PORTFOLIO_TEST_PORT="$port" node - <<'NODE'
const base = `http://127.0.0.1:${process.env.PORTFOLIO_TEST_PORT}`;
const dossier = await fetch(`${base}/api/dossier`);
if (!dossier.ok || !dossier.headers.get("x-portfolio-run-id") || !dossier.headers.get("x-portfolio-source-manifest-sha")) {
  throw new Error("dossier API must return verified release headers");
}
const mutation = await fetch(`${base}/api/dossiers`, { method: "POST" });
if (mutation.status !== 404) {
  throw new Error(`production mutation endpoint must return 404, received ${mutation.status}`);
}
NODE

printf '%s\n' 'public-route verification: passed'
