"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main id="main-content" className="page" role="alert" style={{ padding: "96px var(--gutter) 128px" }}>
      <p className="label">Something went wrong</p>
      <h1 className="title" style={{ marginTop: 12 }}>The page could not be shown.</h1>
      <p className="body" style={{ marginTop: 8 }}>No partial result is displayed. Try again, or reload the page.</p>
      <button className="btn btn-primary" onClick={reset} type="button" style={{ marginTop: 24 }}>
        Try again
      </button>
    </main>
  );
}
