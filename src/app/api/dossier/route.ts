import { NextResponse } from "next/server";

import {
  isPortfolioReleaseError,
  loadPromotedPortfolioRelease,
} from "@/components/dossier/portfolioRelease";
import type { DossierJson } from "@/components/dossier/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const release = await loadPromotedPortfolioRelease();
    return NextResponse.json(release.artifacts.dossier as DossierJson, {
      headers: {
        "Cache-Control": "no-store",
        "X-Portfolio-Run-Id": release.manifest.runId,
        "X-Portfolio-Source-Manifest-Sha": release.manifest.sourceManifest.sha256,
      },
    });
  } catch (error) {
    const code = isPortfolioReleaseError(error) ? error.code : "portfolio_release_unavailable";
    console.error("Promoted portfolio dossier is unavailable:", error);
    return NextResponse.json(
      {
        error: "Promoted portfolio evidence is unavailable or failed integrity checks.",
        code,
      },
      {
        status: 503,
        headers: { "Cache-Control": "no-store" },
      },
    );
  }
}
