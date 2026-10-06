import { ImageResponse } from "next/og";

export const alt = "Abay Avenue signal-retiming evidence dossier";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "stretch",
          background: "#10110f",
          color: "#fffdf8",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          justifyContent: "space-between",
          padding: "68px",
          width: "100%",
        }}
      >
        <div style={{ color: "#f5b25c", display: "flex", fontSize: 28, letterSpacing: 3 }}>
          ALMATY MOBILITY DECISION PLATFORM
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div style={{ display: "flex", fontSize: 72, fontWeight: 700, lineHeight: 1.05 }}>
            Abay Avenue signal-retiming case
          </div>
          <div style={{ color: "#d6d3cc", display: "flex", fontSize: 32 }}>
            Reproducible proxy evidence dossier · not a funding recommendation
          </div>
        </div>
        <div style={{ color: "#aaa79e", display: "flex", fontSize: 24 }}>
          Road geometry is a non-live real-data snapshot.
        </div>
      </div>
    ),
    size,
  );
}
