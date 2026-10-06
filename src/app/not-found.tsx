import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main-content" tabIndex={-1} className="state-page">
      <div className="state-card">
        <p className="state-eyebrow">404 · Outside the release</p>
        <h1 className="state-title">Page not found.</h1>
        <p className="state-copy">This route is not part of the published portfolio case study.</p>
        <Link className="state-action" href="/scenarios/abay-signal-retiming/dossier">
          Open the Abay case dossier
        </Link>
      </div>
    </main>
  );
}
