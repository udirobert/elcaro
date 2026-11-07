import { ImageResponse } from "next/og";

export const alt = "The IPI Benchmark — 24 injection tasks, two conditions, ~1,300 transcripts";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Per-tool OG for the proving ground — light product chrome, benchmark accent
// (safe teal) and its own hook.
export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#FAFAF8",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 6,
            background: "linear-gradient(90deg, #1A8A7A, #E5533D, #7C3AED)",
          }}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "0 72px",
            flex: 1,
          }}
        >
          <div
            style={{
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: "4px",
              textTransform: "uppercase",
              color: "#1A8A7A",
            }}
          >
            The IPI Benchmark
          </div>
          <div
            style={{
              fontSize: 76,
              fontWeight: 900,
              letterSpacing: "-3px",
              color: "#1A1A18",
              lineHeight: 1.05,
              marginTop: 14,
              display: "flex",
              flexDirection: "column",
            }}
          >
            Frontier models fall
            <br />
            when labels disappear.
          </div>
          <div
            style={{
              fontSize: 28,
              color: "#6B6B68",
              lineHeight: 1.4,
              marginTop: 22,
              maxWidth: 980,
            }}
          >
            24 injection tasks, two deployment conditions, ~1,300 transcripts —
            and a detector scorecard on the same payloads.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "0 72px 44px",
            fontSize: 16,
            color: "#A3A3A0",
          }}
        >
          <div>detect · quarantine · act</div>
          <div>elcaro.trustfall.xyz/evaluate/benchmark</div>
        </div>
      </div>
    ),
    { ...size },
  );
}
