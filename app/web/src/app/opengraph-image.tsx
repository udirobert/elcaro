import { ImageResponse } from "next/og";

export const alt = "Elcaro — Prompt injection detection for AI agents";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: "#FAFAF8",
          padding: "80px",
        }}
      >
        {/* Decorative gradient bar at top */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "6px",
            background: "linear-gradient(90deg, #7C3AED, #F97066, #14B8A6)",
          }}
        />

        {/* Main content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "24px",
          }}
        >
          <h1
            style={{
              fontSize: "72px",
              fontWeight: 900,
              color: "#1A1A18",
              letterSpacing: "-2px",
              lineHeight: 1.1,
              textAlign: "center",
              margin: 0,
            }}
          >
            elcaro
          </h1>

          <p
            style={{
              fontSize: "28px",
              color: "#6B6B68",
              textAlign: "center",
              lineHeight: 1.4,
              maxWidth: "700px",
              margin: 0,
            }}
          >
            Prompt injection detection for autonomous agents
          </p>

          {/* Technique classes as a visual row */}
          <div
            style={{
              display: "flex",
              gap: "12px",
              marginTop: "32px",
            }}
          >
            {["A", "B", "C", "D", "E", "F"].map((letter) => (
              <div
                key={letter}
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "12px",
                  backgroundColor: "#F4F4F2",
                  border: "1px solid #E8E8E4",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "20px",
                  fontWeight: 900,
                  color: "#7C3AED",
                }}
              >
                {letter}
              </div>
            ))}
          </div>
        </div>

        {/* Bottom tagline */}
        <p
          style={{
            position: "absolute",
            bottom: "40px",
            fontSize: "16px",
            color: "#A3A3A0",
            margin: 0,
          }}
        >
          oracle, reversed · github.com/udirobert/elcaro
        </p>
      </div>
    ),
    { ...size }
  );
}
