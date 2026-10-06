import { NextRequest, NextResponse } from "next/server";

import {
  isPortfolioReleaseError,
  loadPromotedPortfolioRelease,
  loadVerifiedPortfolioDownload,
} from "@/components/dossier/portfolioRelease";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function errorStatus(code: string) {
  if (code === "download_not_found" || code === "manifest_missing") return 404;
  if (code === "manifest_contract_invalid" || code === "manifest_path_invalid") return 400;
  if (code === "mixed_release" || code === "artifact_stale" || code === "artifact_invalid") return 409;
  return 503;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ artifactId: string }> },
) {
  const { artifactId } = await context.params;
  const requestedRunId = request.nextUrl.searchParams.get("runId") ?? undefined;

  try {
    const release = await loadPromotedPortfolioRelease(process.cwd(), requestedRunId);
    const { artifact, content } = await loadVerifiedPortfolioDownload(release, artifactId);
    const cacheControl = requestedRunId ? "public, max-age=31536000, immutable" : "no-store";

    return new NextResponse(new Uint8Array(content), {
      headers: {
        "Cache-Control": cacheControl,
        "Content-Disposition": `attachment; filename="${artifact.filename}"`,
        "Content-Length": String(content.byteLength),
        "Content-Type": `${artifact.mediaType}; charset=utf-8`,
        "X-Content-Type-Options": "nosniff",
        "X-Portfolio-Artifact-Sha256": artifact.sha256,
        "X-Portfolio-Download-Id": artifact.id,
        "X-Portfolio-Run-Id": release.manifest.runId,
        "X-Portfolio-Source-Manifest-Sha": release.manifest.sourceManifest.sha256,
      },
    });
  } catch (error) {
    const code = isPortfolioReleaseError(error) ? error.code : "portfolio_release_unavailable";
    if (!isPortfolioReleaseError(error)) {
      console.error("Immutable portfolio download failed:", error);
    }
    return NextResponse.json(
      {
        error: "The requested evidence download is unavailable or failed integrity checks.",
        code,
      },
      {
        status: errorStatus(code),
        headers: { "Cache-Control": "no-store" },
      },
    );
  }
}
