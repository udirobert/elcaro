import { ImageResponse } from "next/og";

export const alt = "Elcaro — detect indirect prompt injection before your agent acts";
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
          backgroundColor: "#FAFAF8",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        {/* Decorative gradient bar at top */}
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

        {/* Header row */}
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
            prompt-injection scanner · open source
          </div>
        </div>

        {/* Main: the score */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "0 72px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                fontSize: 24,
                fontWeight: 900,
                letterSpacing: "1px",
                color: "#FFFFFF",
                backgroundColor: "#E5533D",
                padding: "9px 20px",
                borderRadius: 999,
              }}
            >
              DANGEROUS
            </div>
            <div style={{ fontSize: 22, color: "#6B6B68" }}>
              indirect prompt injection · risk 1.00
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 20,
              marginTop: 10,
            }}
          >
            <div
              style={{
                fontSize: 210,
                fontWeight: 900,
                letterSpacing: "-8px",
                color: "#E5533D",
                lineHeight: 1,
              }}
            >
              1.00
            </div>
            <div style={{ fontSize: 26, color: "#6B6B68" }}>detected</div>
          </div>

          {/* subtle scan beam */}
          <div
            style={{
              height: 4,
              width: "100%",
              maxWidth: 720,
              borderRadius: 999,
              marginTop: 18,
              background: "linear-gradient(90deg, transparent, #7C3AED, #F97066, transparent)",
            }}
          />

          <div
            style={{
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: "-1px",
              color: "#1A1A18",
              marginTop: 26,
            }}
          >
            See what your agent can&apos;t — scan before it reasons.
          </div>
        </div>

        {/* Footer */}
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
          <div>github.com/udirobert/elcaro</div>
        </div>
      </div>
    ),
    { ...size }
  );
}
