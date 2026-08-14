import { NextRequest, NextResponse } from "next/server";

import { POST as regeneratePortfolio } from "@/app/api/dossiers/route";
import {
  isPortfolioReleaseError,
  loadPromotedPortfolioRelease,
  parseRouteManifest,
} from "@/components/dossier/portfolioRelease";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE_HEADERS = { "Cache-Control": "no-store" } as const;
const GENERATION_STATUSES = new Set([
  "promoted",
  "promoted_with_alias_error",
  "promoted_with_warning",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function generationEnabled() {
  return (
    process.env.TRAFFIC_SIM_ENABLE_PORTFOLIO_GENERATION === "1" &&
    process.env.NODE_ENV !== "production"
  );
}

export async function GET() {
  try {
    const release = await loadPromotedPortfolioRelease();

    return NextResponse.json(release.artifacts.procurementPack, {
      headers: {
        ...NO_STORE_HEADERS,
        "X-Portfolio-Run-Id": release.manifest.runId,
        "X-Portfolio-Source-Manifest-Sha": release.manifest.sourceManifest.sha256,
      },
    });
  } catch (error) {
    const code = isPortfolioReleaseError(error) ? error.code : "portfolio_release_unavailable";
    console.error("Promoted procurement pack is unavailable:", error);
    return NextResponse.json(
      {
        error: "Promoted procurement evidence is unavailable or failed integrity checks.",
        code,
      },
      {
        status: 503,
        headers: NO_STORE_HEADERS,
      },
    );
  }
}

export async function POST(request: NextRequest) {
  if (!generationEnabled()) {
    return NextResponse.json(
      { error: "Not found." },
      { status: 404, headers: NO_STORE_HEADERS },
    );
  }

  // The canonical bootstrap transaction generates and promotes every portfolio
  // artifact together. Reusing that boundary keeps this compatibility endpoint
  // subject to the same request, process, lock, timeout, and release checks.
  const generationResponse = await regeneratePortfolio(request);
  if (generationResponse.status !== 201) return generationResponse;

  try {
    const generationPayload: unknown = await generationResponse.json();
    if (!isRecord(generationPayload) || !isRecord(generationPayload.generation)) {
      throw new Error("The canonical generation response is incomplete.");
    }
    const generationStatus = generationPayload.generation.status;
    if (typeof generationStatus !== "string" || !GENERATION_STATUSES.has(generationStatus)) {
      throw new Error("The canonical generation response has an invalid status.");
    }

    const generatedManifest = parseRouteManifest(generationPayload.manifest);
    const release = await loadPromotedPortfolioRelease(process.cwd(), generatedManifest.runId);
    const expectedPack = generatedManifest.artifacts.find(
      (artifact) => artifact.role === "procurementPack",
    );
    const actualPack = release.manifest.artifacts.find(
      (artifact) => artifact.role === "procurementPack",
    );
    if (
      release.manifest.sourceManifest.sha256 !== generatedManifest.sourceManifest.sha256 ||
      !expectedPack ||
      !actualPack ||
      expectedPack.logicalPath !== actualPack.logicalPath ||
      expectedPack.sha256 !== actualPack.sha256 ||
      expectedPack.bytes !== actualPack.bytes
    ) {
      throw new Error("The promoted procurement pack no longer matches the generated release.");
    }

    return NextResponse.json(
      {
        manifest: release.manifest,
        generation: generationPayload.generation,
        procurementPack: release.artifacts.procurementPack,
      },
      {
        status: 201,
        headers: {
          ...NO_STORE_HEADERS,
          "X-Portfolio-Run-Id": release.manifest.runId,
          "X-Portfolio-Source-Manifest-Sha": release.manifest.sourceManifest.sha256,
        },
      },
    );
  } catch (error) {
    const code = isPortfolioReleaseError(error)
      ? error.code
      : "procurement_generation_binding_failed";
    console.error("Generated procurement pack could not be bound to its release:", error);
    return NextResponse.json(
      {
        error: "Generated procurement evidence failed immutable release checks.",
        code,
      },
      {
        status: 503,
        headers: NO_STORE_HEADERS,
      },
    );
  }
}
