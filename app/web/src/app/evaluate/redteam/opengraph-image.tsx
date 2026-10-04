import { ImageResponse } from "next/og";

export const alt = "The Red Team — Elcaro's evolutionary searcher attacks its own engine";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Per-tool OG for the proving ground — light product chrome like the root
// card, with the tool's accent color (coral) and its own hook.
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
            background: "linear-gradient(90deg, #7C3AED, #F97066, #14B8A6)",
          }}
        />

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "46px 72px 0",
          }}
        >
          <div style={{ fontSize: 30, fontWeight: 900, letterSpacing: "-1px", color: "#1A1A18" }}>
            elcaro
          </div>
          <div
            style={{
              fontSize: 15,
              color: "#A3A3A0",
              border: "1px solid #E8E8E4",
              borderRadius: 999,
              padding: "5px 14px",
            }}
          >
            proving ground · live engine
          </div>
        </div>

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "0 72px",
          }}
        >
          <div
            style={{
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: "4px",
              textTransform: "uppercase",
              color: "#F97066",
            }}
          >
            The Red Team
          </div>
          <div
            style={{
              fontSize: 88,
              fontWeight: 900,
              letterSpacing: "-3px",
              color: "#1A1A18",
              lineHeight: 1.05,
              marginTop: 14,
            }}
          >
            Elcaro attacks itself.
          </div>
          <div
            style={{
              fontSize: 28,
              color: "#6B6B68",
              lineHeight: 1.4,
              marginTop: 22,
              maxWidth: 940,
            }}
          >
            An evolutionary adversarial searcher mutates the attack corpus and
            hunts for bypasses — live, against the production engine.
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
          <div>elcaro.trustfall.xyz/evaluate/redteam</div>
        </div>
      </div>
    ),
    { ...size },
  );
}
