"use client";

import { useRef, useCallback } from "react";
import styles from "./tangem-stage.module.css";

export type StagePhase = "idle" | "pending" | "success" | "failed";

const VIEW_W = 640;
const VIEW_H = 340;
const FIN_X = VIEW_W * 0.5;
const MID_Y = VIEW_H * 0.52;

// Deterministic signal ribbon — 28 generated sine paths whose amplitude
// envelope collapses to zero at the fin. Same bytes every render; nothing
// is sampled from an asset.
const RIBBON_LINES: { d: string; opacity: number }[] = (() => {
  const lines: { d: string; opacity: number }[] = [];
  for (let i = 0; i < 28; i += 1) {
    const spread = (i - 13.5) / 13.5; // -1..1
    const baseY = MID_Y + spread * 130;
    const points: string[] = [];
    const steps = 16;
    for (let s = 0; s <= steps; s += 1) {
      const x = (s / steps) * FIN_X;
      const env = Math.pow(1 - x / FIN_X, 1.55);
      const y =
        MID_Y +
        (baseY - MID_Y) * env +
        Math.sin(x * 0.055 + i * 0.7) * 7 * env;
      points.push(`${s === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`);
    }
    lines.push({ d: points.join(" "), opacity: 0.16 + Math.abs(spread) * 0.22 });
  }
  return lines;
})();

export function TangemStageArt({
  phase,
  reduceMotion,
}: {
  phase: StagePhase;
  reduceMotion: boolean;
}) {
  const tiltRef = useRef<HTMLDivElement>(null);

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const tilt = tiltRef.current;
      if (!tilt || reduceMotion || e.pointerType === "touch") return;
      // normalized over the whole stage, clamped so tilt stays within ±6deg
      const r = e.currentTarget.getBoundingClientRect();
      const clamp = (v: number) => Math.max(-0.5, Math.min(0.5, v));
      const px = clamp((e.clientX - r.left) / r.width - 0.5);
      const py = clamp((e.clientY - r.top) / r.height - 0.5);
      // bounded ±6deg; specular shifts with the tilt
      tilt.style.setProperty("--rx", `${(-py * 12).toFixed(2)}deg`);
      tilt.style.setProperty("--ry", `${(px * 12).toFixed(2)}deg`);
      tilt.style.setProperty("--sheen", `${115 - px * 40}deg`);
    },
    [reduceMotion]
  );

  const onPointerLeave = useCallback(() => {
    const tilt = tiltRef.current;
    if (!tilt) return;
    // spring home — CSS transition eases it back
    tilt.style.setProperty("--rx", "0deg");
    tilt.style.setProperty("--ry", "0deg");
    tilt.style.setProperty("--sheen", "115deg");
  }, []);

  return (
    <div
      className={styles.stage}
      data-phase={phase}
      data-motion={reduceMotion ? "static" : "live"}
      role="img"
      aria-label="Instrument still life: a signal ribbon converges and stops at a frosted glass fin beside a physical Tangem card."
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      <svg
        className={styles.ribbon}
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        preserveAspectRatio="xMidYMid slice"
        aria-hidden
      >
        <defs>
          <linearGradient id="tg-ribbon" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#5b8ff0" />
            <stop offset="0.75" stopColor="#3fc7c0" />
            <stop offset="1" stopColor="#8fe8d8" />
          </linearGradient>
        </defs>
        {RIBBON_LINES.map((l, i) => (
          <path
            key={i}
            d={l.d}
            fill="none"
            stroke="url(#tg-ribbon)"
            strokeWidth="1"
            strokeOpacity={l.opacity}
          />
        ))}
      </svg>

      <div className={styles.fin} aria-hidden />
      <div className={styles.sweep} aria-hidden />
      <div className={styles.sweepBack} aria-hidden />

      <div className={styles.cardRig}>
        <div className={styles.cardTilt} ref={tiltRef}>
          <div className={styles.cardBack} aria-hidden />
          <div className={styles.card} aria-hidden>
            <div className={styles.nfc}>
              <span className={styles.nfcArc} />
              <span className={styles.nfcArc} />
              <span className={styles.nfcArc} />
            </div>
            <span className={styles.wordmark}>TANGEM</span>
            <span className={styles.wordmarkSub}>YOUR CARD · YOUR KEYS</span>
          </div>
        </div>
      </div>
    </div>
  );
}
