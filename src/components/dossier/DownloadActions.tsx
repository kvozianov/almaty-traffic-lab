"use client";

import { useState } from "react";

export type DownloadArtifact = {
  id: string;
  label: string;
  logicalPath: string;
  sha256?: string | null;
  bytes?: number | null;
};

type DownloadActionsProps = {
  artifacts: DownloadArtifact[];
  runId: string;
  releaseGeneratedAt: string;
  sourceManifestSha256: string;
};

function formatBytes(bytes?: number | null) {
  if (typeof bytes !== "number" || !Number.isFinite(bytes)) return "not recorded";
  return `${new Intl.NumberFormat("en").format(bytes)} bytes`;
}

export default function DownloadActions({
  artifacts,
  runId,
  releaseGeneratedAt,
  sourceManifestSha256,
}: DownloadActionsProps) {
  const [status, setStatus] = useState("Choose an export to request a read-only, release-bound file.");

  function handleDownload(label: string) {
    setStatus(`${label} requested. Your browser will handle the download.`);
  }

  function handlePrint() {
    setStatus("Print dialog requested. Saving as PDF is handled by your browser.");
    window.print();
  }

  return (
    <section className="rounded-[10px] border border-[var(--line)] bg-[var(--surface)] p-5 text-[var(--ink)] sm:p-6" aria-labelledby="download-actions-title" data-print-hidden>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">Exports</p>
          <h2 id="download-actions-title" className="mt-2 [font-family:var(--font-editorial)] text-2xl font-semibold tracking-[-0.025em] text-[var(--ink)]">
            Download the current evidence
          </h2>
          <p className="mt-2 max-w-[70ch] text-sm leading-6 text-[var(--muted)]">
            Each file is read-only and bound to the promoted Abay release shown below.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {artifacts.map((artifact) => (
          <a
            key={artifact.id}
            href={`/api/downloads/${artifact.id}?runId=${encodeURIComponent(runId)}`}
            onClick={() => handleDownload(artifact.label)}
            className="group flex min-h-12 items-center justify-between gap-3 rounded-md border border-[var(--line-strong)] bg-[var(--surface-raised)] px-3.5 py-3 text-sm font-medium text-[var(--ink)] outline-none transition-colors hover:border-[var(--sage)] hover:bg-[var(--sage-wash)] focus-visible:ring-2 focus-visible:ring-[var(--sage)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)]"
          >
            <span>{artifact.label}</span>
            <span aria-hidden="true" className="shrink-0 text-[var(--sage)]">↓</span>
          </a>
        ))}
        <button
          type="button"
          onClick={handlePrint}
          className="group flex min-h-12 items-center justify-between gap-3 rounded-md border border-[var(--line-strong)] bg-[var(--surface-raised)] px-3.5 py-3 text-left text-sm font-medium text-[var(--ink)] outline-none transition-colors hover:border-[var(--sage)] hover:bg-[var(--sage-wash)] focus-visible:ring-2 focus-visible:ring-[var(--sage)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)]"
        >
          <span>Print / save as PDF</span>
          <span aria-hidden="true" className="shrink-0 text-[var(--sage)]">↗</span>
        </button>
      </div>

      <p className="mt-4 rounded-md bg-[var(--sage-wash)] px-3 py-2 text-sm text-[var(--sage)]" role="status" aria-live="polite">
        {status}
      </p>

      <details className="mt-5 border-t border-[var(--line)] pt-4">
        <summary className="min-h-11 cursor-pointer rounded-sm py-3 font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--muted)] outline-none hover:text-[var(--ink)] focus-visible:ring-2 focus-visible:ring-[var(--sage)]">
          Technical details
        </summary>
        <dl className="mt-3 grid gap-4 text-sm text-[var(--muted)] md:grid-cols-2">
          <div>
            <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Release run</dt>
            <dd className="mt-1 break-all font-mono text-[11px] text-[var(--ink)]">{runId}</dd>
          </div>
          <div>
            <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Release generated</dt>
            <dd className="mt-1 font-mono text-[11px] text-[var(--ink)]">{releaseGeneratedAt}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Source manifest SHA-256</dt>
            <dd className="mt-1 break-all font-mono text-[11px] text-[var(--ink)]">{sourceManifestSha256}</dd>
          </div>
        </dl>

        <div className="mt-4 divide-y divide-[var(--line)] rounded-lg border border-[var(--line)] bg-[var(--surface-raised)]">
          {artifacts.map((artifact) => (
            <div key={artifact.id} className="px-3.5 py-3">
              <p className="font-medium text-[var(--ink)]">{artifact.label}</p>
              <p className="mt-1 break-all font-mono text-[11px] text-[var(--muted)]">ID: {artifact.id}</p>
              <p className="mt-1 break-all font-mono text-[11px] text-[var(--muted)]">Path: {artifact.logicalPath}</p>
              <p className="mt-1 break-all font-mono text-[11px] text-[var(--muted)]">
                SHA-256: {artifact.sha256 ?? "not recorded"} · {formatBytes(artifact.bytes)}
              </p>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
