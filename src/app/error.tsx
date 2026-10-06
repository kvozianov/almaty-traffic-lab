"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main id="main-content" tabIndex={-1} className="state-page" role="alert">
      <div className="state-card">
        <p className="state-eyebrow">Evidence boundary</p>
        <h1 className="state-title">Evidence is unavailable.</h1>
        <p className="state-copy">The dossier could not be loaded safely. No partial KPI result is shown.</p>
        <button className="state-action" onClick={reset} type="button">Try again</button>
      </div>
    </main>
  );
}
