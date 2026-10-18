---
workflow: product-launch-video
flow: automation
storyboard: no
message: "A $0.01 gate, paid through your own vault, reads the paragraph before your agent acts."
destination: web-embed
aspect: 1920x1080
language: en
length: 80s
angle: threat-first promo
---

## Intent

A hackathon submission promo for Elcaro's PayBox integration: show judges that an
agent which moves real money can be steered by a poisoned vendor email, and that
Elcaro catches it at a paid gate. Sell, not tour — story-driven, threat-first,
terminal register. The previous three cuts were rejected for weak storytelling and
illegible UI, so narrative clarity and on-screen legibility outrank novelty.

## Assets

- ../../demo-video/paybox/take-terminal.cast — real mainnet run (asciinema, 80x24). Source of truth for the terminal beats; typeset from this, never screen-grabbed.
- /Users/udingethe/Desktop/Screen Recording 2026-10-17 at 22.26.46.mov — the same run as a desktop grab. Reference only; do not feature (window occupies ~15% of frame).
- ../../demo-video/paybox/shot-a-heist.webm, shot-b-volley.webm, shot-c-xray.webm — 1280x634 light-theme UI captures. Superseded by the Step 1 re-capture.
- https://elcaro.trustfall.xyz/paybox — the gauntlet page; primary capture target.

## Customizations

- Narration + music bed. Narration carries the story spine; music ducks under it.
- Terminal scenes are typeset as live HTML from `take-terminal.cast` at large point size, so the proof block (`risk 0.73 · DANGEROUS · signed 3383cee9…`) is readable on a phone.
- Punch-in zooms onto the captured UI's verdict rows and stat counters rather than full-page views.
- The BLEED moment (unguarded agent approving a forged payee) must land inside the first 10 seconds.

## Notes

- Legibility is the failure mode being fixed: no light-grey-on-white text left small in frame, no black letterbox bars around a desktop grab, no "Powered by Netlify" badge visible.
- Real artefacts only — the $0.01 Base mainnet settlement and the signed verdict are the credibility payload; do not fake or stylise them into unreadability.
- Deliver final MP4 to ~/Downloads for review; submission is due the same night.
- Numbers to keep exact: 6 scenarios, 5 attacks stopped, $24,600 protected, $0.01 per gate.
