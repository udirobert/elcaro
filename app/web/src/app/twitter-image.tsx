import { ImageResponse } from "next/og";

export const alt = "Elcaro — Prompt injection detection for AI agents";
export const size = { width: 1200, height: 628 };
export const contentType = "image/png";

export default function TwitterImage() {
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
            See what your agent can&apos;t
          </p>
        </div>
        <p
          style={{
            position: "absolute",
            bottom: "40px",
            fontSize: "16px",
            color: "#A3A3A0",
            margin: 0,
          }}
        >
          Prompt injection detection · github.com/udirobert/elcaro
        </p>
      </div>
    ),
    { ...size }
  );
}
