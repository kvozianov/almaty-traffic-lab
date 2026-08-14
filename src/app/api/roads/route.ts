import { NextRequest, NextResponse } from "next/server";

import {
  isPortfolioReleaseError,
  loadPromotedPortfolioRelease,
  validateRoadProviderEvidence,
} from "@/components/dossier/portfolioRelease";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fail(message: string): never {
  throw new Error(message);
}

function parseRoads(content: Buffer): Record<string, unknown> {
  let payload: unknown;
  try {
    // The imported snapshot contains legacy bare NaN tokens. Integrity is
    // checked against the raw immutable bytes before this JSON-safe view is built.
    const jsonSafe = content
      .toString("utf8")
      .replace(/([:[,\[]\s*)NaN(?=\s*[,}\]])/g, "$1null");
    payload = JSON.parse(jsonSafe);
  } catch {
    fail("The immutable roads source is not valid JSON.");
  }
  if (!isRecord(payload) || payload.type !== "FeatureCollection" || !Array.isArray(payload.features)) {
    fail("The immutable roads source is not a GeoJSON FeatureCollection.");
  }
  return payload;
}

export async function GET(request: NextRequest) {
  const requestedRunId = request.nextUrl.searchParams.get("runId") ?? undefined;

  try {
    const release = await loadPromotedPortfolioRelease(process.cwd(), requestedRunId);
    const roadsSource = release.sources.roadsGeojson;
    if (!roadsSource) fail("The immutable release does not declare a roadsGeojson source.");
    const roads = parseRoads(roadsSource.content);
    const provider = validateRoadProviderEvidence(
      release.artifacts.providers,
      roadsSource,
      (roads.features as unknown[]).length,
    );

    return NextResponse.json(
      { ...roads, providerStatus: provider },
      {
        headers: {
          "Cache-Control": "no-store",
          "X-Portfolio-Run-Id": release.manifest.runId,
          "X-Portfolio-Source-Sha256": roadsSource.sha256,
        },
      },
    );
  } catch (error) {
    const code = isPortfolioReleaseError(error) ? error.code : "roads_evidence_invalid";
    const status =
      code === "manifest_contract_invalid" || code === "manifest_path_invalid"
        ? 400
        : code === "manifest_missing"
          ? 404
          : 503;
    if (!isPortfolioReleaseError(error)) {
      console.error("Immutable roads evidence failed validation:", error);
    }
    return NextResponse.json(
      { error: "Verified road geometry is unavailable.", code },
      { status, headers: { "Cache-Control": "no-store" } },
    );
  }
}
