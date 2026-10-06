import TrafficMap from "@/components/TrafficMap";

const DOSSIER_PATH = "/scenarios/abay-signal-retiming/dossier";

export default function SandboxPage() {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      style={{
        minHeight: "100dvh",
        background: "#F5F3EE",
        color: "#1D221F",
      }}
    >
      <section
        aria-label="Demo sandbox data disclaimer"
        style={{
          borderBottom: "1px solid #DCDDD7",
          background: "#FCFBF8",
        }}
      >
        <div
          style={{
            display: "flex",
            width: "min(100% - 32px, 1320px)",
            minHeight: "64px",
            margin: "0 auto",
            alignItems: "center",
            gap: "12px 24px",
            flexWrap: "wrap",
            padding: "10px 0",
          }}
        >
          <p style={{ flex: "1 1 420px", margin: 0, fontSize: "0.9375rem", lineHeight: 1.55 }}>
            Interactive demo sandbox — uses demo and proxy data. It is not live traffic, calibrated evidence, or a funding recommendation.
          </p>
          <a
            href={DOSSIER_PATH}
            style={{
              display: "inline-flex",
              minHeight: "44px",
              alignItems: "center",
              color: "#526A5B",
              fontSize: "0.875rem",
              fontWeight: 650,
              textDecorationColor: "#BFC4BE",
              textUnderlineOffset: "4px",
            }}
          >
            Open the evidence dossier
          </a>
          <details style={{ flex: "0 1 auto", color: "#656B66", fontSize: "0.8125rem" }}>
            <summary
              style={{
                display: "inline-flex",
                minHeight: "44px",
                alignItems: "center",
                cursor: "pointer",
                textDecoration: "underline",
                textDecorationColor: "#DCDDD7",
                textUnderlineOffset: "4px",
              }}
            >
              Privacy note
            </summary>
            <p style={{ maxWidth: "62ch", margin: "0 0 8px", lineHeight: 1.55 }}>
              The CARTO basemap may receive standard network metadata. Scenario selections, local identifiers, and analytics
              data are not sent.
            </p>
          </details>
        </div>
      </section>
      <TrafficMap />
    </main>
  );
}
