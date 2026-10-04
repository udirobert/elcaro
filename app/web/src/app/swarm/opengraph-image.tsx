import { ImageResponse } from "next/og";

export const alt =
  "Elcaro Swarm — Class G steering rules matched records across two real agent-swarms";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Case-file OG for the swarm forensics page — matches the dashboard
// artifact's dark forensic-console aesthetic rather than the site's light
// chrome, since the shared card IS the case file.
export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#0b0e14",
          fontFamily: "monospace",
          padding: "64px 72px",
          position: "relative",
        }}
      >
        {/* Amber case-file accent bar */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            bottom: 0,
            width: 8,
            background: "#ffd479",
          }}
        />

        <div
          style={{
            fontSize: 22,
            letterSpacing: 6,
            textTransform: "uppercase",
            color: "#ffd479",
          }}
        >
          Case file — swarm forensics
        </div>

        <div
          style={{
            fontSize: 54,
            fontWeight: 700,
            color: "#eef2fa",
            lineHeight: 1.15,
            marginTop: 28,
            maxWidth: 1000,
          }}
        >
          Class G steering rules matched records across two real agent
          swarms — a register the classic detectors didn&apos;t model.
        </div>

        <div
          style={{
            fontSize: 26,
            color: "#9fb0cc",
            lineHeight: 1.4,
            marginTop: 24,
            maxWidth: 960,
          }}
        >
          15,005 records match Class G agent→agent steering rules — the
          largest single tag class on the Wiki corpus, #2 on AI Village, a
          corpus it was never tuned on.
        </div>

        <div
          style={{
            display: "flex",
            gap: 56,
            marginTop: "auto",
            fontSize: 24,
          }}
        >
          {[
            ["209,890", "messages"],
            ["13,927", "propagated artifacts"],
            ["59", "evasion pages"],
            ["2", "corpora"],
          ].map(([n, label]) => (
            <div key={label} style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ color: "#7ee0a3", fontWeight: 700 }}>{n}</div>
              <div
                style={{
                  color: "#7f8ba3",
                  fontSize: 17,
                  textTransform: "uppercase",
                  letterSpacing: 2,
                  marginTop: 4,
                }}
              >
                {label}
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            position: "absolute",
            top: 64,
            right: 72,
            fontSize: 22,
            fontWeight: 700,
            color: "#7ee0a3",
          }}
        >
          elcaro
        </div>
      </div>
    ),
    { ...size },
  );
}
