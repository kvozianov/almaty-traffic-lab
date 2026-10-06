export default function Loading() {
  return (
    <main id="main-content" tabIndex={-1} className="state-page">
      <div className="state-card" role="status" aria-live="polite">
        <p className="state-eyebrow">Source-bound release</p>
        <p className="state-title">Preparing the evidence dossier.</p>
        <p className="state-copy">Verifying the promoted run and its immutable artifacts.</p>
        <div className="state-progress" aria-hidden="true" />
      </div>
    </main>
  );
}
