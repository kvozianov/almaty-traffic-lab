#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

image_ref=${PORTFOLIO_RUNTIME_IMAGE:-project1-citytraffic-app:latest}
output_dir=${PORTFOLIO_SECURITY_OUTPUT_DIR:-reports/security}
mkdir -p "$output_dir"
output_dir=$(CDPATH= cd -- "$output_dir" && pwd)

temporary_root=$(mktemp -d "${TMPDIR:-/tmp}/portfolio-security.XXXXXX")
cleanup() {
  rm -rf "$temporary_root"
}
trap cleanup EXIT HUP INT TERM
printf '%s\n' '{}' > "$temporary_root/config.json"

syft_image='docker.io/anchore/syft:v1.50.0@sha256:1288ea4c8b38767b4e620c1e312c8cb26b6e887a99b4f07ab6cd19fc6f225026'
grype_image='docker.io/anchore/grype:v0.116.1@sha256:1e71065c0a4cff3e6bd3b8add525ffac4343eb4971694eb90a31cf6d4d3e85db'
semgrep_image='docker.io/semgrep/semgrep:1.153.0@sha256:6fe804189b0cc51d2f174882a228666ddb8835685bced62ab3aa8b231b7e6af1'

# Scanner pulls use an isolated empty Docker config. This avoids invoking a
# workstation credential helper for public, digest-pinned images.
for scanner_image in "$syft_image" "$grype_image" "$semgrep_image"; do
  DOCKER_CONFIG="$temporary_root" docker pull "$scanner_image"
done

if ! docker image inspect "$image_ref" >/dev/null 2>&1; then
  docker compose build
fi

archive="$temporary_root/runtime-image.tar"
docker save "$image_ref" -o "$archive"
docker run --rm -v "$archive:/scan/runtime-image.tar:ro" "$syft_image" \
  docker-archive:/scan/runtime-image.tar -o cyclonedx-json > "$output_dir/v0.1.0-runtime-sbom.cdx.json"
docker run --rm -v "$output_dir:/scan:ro" "$grype_image" \
  sbom:/scan/v0.1.0-runtime-sbom.cdx.json -o json > "$output_dir/v0.1.0-runtime-grype.json"
docker run --rm -v "$repository_root:/src:ro" "$semgrep_image" \
  semgrep --config /src/.semgrep.yml /src --json > "$output_dir/v0.1.0-semgrep.json"

node - "$output_dir" <<'NODE'
const fs = require("fs");
const path = require("path");
const outputDir = process.argv[2];
const sbom = JSON.parse(fs.readFileSync(path.join(outputDir, "v0.1.0-runtime-sbom.cdx.json"), "utf8"));
const grype = JSON.parse(fs.readFileSync(path.join(outputDir, "v0.1.0-runtime-grype.json"), "utf8"));
const semgrep = JSON.parse(fs.readFileSync(path.join(outputDir, "v0.1.0-semgrep.json"), "utf8"));
const severity = {};
for (const match of grype.matches) {
  const level = match.vulnerability.severity;
  severity[level] = (severity[level] ?? 0) + 1;
}
const summary = {
  schemaVersion: "portfolio-security-scan/v1",
  sbomComponents: sbom.components.length,
  grypeSeverity: severity,
  semgrepFindings: semgrep.results.length,
  passed: (severity.Critical ?? 0) === 0 && (severity.High ?? 0) === 0 && semgrep.results.length === 0,
};
fs.writeFileSync(path.join(outputDir, "v0.1.0-security-summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary));
process.exit(summary.passed ? 0 : 1);
NODE
