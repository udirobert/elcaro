# Hermes video — production playbook (fframes)

Working reference for the Nov-11 hackathon film. Shot lists live at
`demo-video/hermes/SHOTLIST.md`; this doc is the *how* — the fframes
workflow and the anti-slop rules, from the fframes skill docs
(`design.md`, `SKILL.md`) and launch-video research.

## Brief (pin before any code)

- **Audience:** judges (Typeform video) + X feed (separate cut).
- **One thing remembered:** *"the breach replayed — and stopped."*
- **Tone:** dread → relief → proof. Tense minimal synth, dark ground.
- **Never invent:** every headline card cites source + date (verified
  incidents — see SHOTLIST.md canon table). No fake numbers, ever.
- **Assets:** live pane/terminal takes; Satoshi fonts
  (`videos/elcaro-paybox/capture/assets/fonts/`); narrate.mjs VO.

## The fframes doctrine (skill's own rules)

1. **Sound first.** Pick the soundtrack before designing motion; the
   beat grid sets every timing. VO segments recorded first — each live
   scene is one-per-spoken-segment, so voice defines the edit.
2. **The no-slop test:** *"would this work for a different product with
   only the text changed? If yes, change the idea, not the colors."*
   Ours passes (our pane, our incidents) — but every produced scene
   needs a motion idea tied to its subject, never `fade-up-40px` × N.
3. **Everything is the Rust crate + `media/`.** No external ffmpeg
   joins/grades. Footage comes in as `Clip::new("take.mov", a..b)`;
   `clip.image(&frame, ctx)` crops the pane *in the scene* — the
   "crop to the row" rule is code, not a note to self.

## Hard numbers (design.md — bind these)

- Reading: 3 words/s + 1 s to notice. ~8 words/line, ~3 lines/card.
- Scenes: title 2.5–4 s, content 4–8 s, outro 2–3 s. Hook lands <1.5 s.
- Entrances 0.3–0.6 s; exits 0.2–0.3 s; holds 1–3 s with ambient motion.
- Type (1920×1080): hero 140–200, title 96–120, body 44–60, floor 28 px.
- Margins 8–10% width. One font family (two max: display + text).
- Easings: `EaseOut` entrances, `EaseIn` exits, `EaseInOut` camera;
  `Spring { mass 1.0, stiffness 150, damping 18 }` for friendly pop.
  Staggers: items 60–120 ms, words 20–40 ms.
- One focal motion at a time; secondary elements move less + later.
- Lower-third recipe (documented): bar slides 0.5 s EaseOut → name
  +0.15 s → role +0.1 s → hold → all exit 0.25 s. Use verbatim for
  "EchoLeak, replayed" overlays.
- Transitions: `Overlap::Previous(0.4)` cross-fade, or push ±80 px.
  Check `Scene@end` + next first frame + `onion` for flashes.

## Scene-by-scene motion plan (V2 montage cut)

| Scene | Motion idea (subject-tied, anti-slop) |
|---|---|
| Headline montage ×4 | NOT identical cards: incident dossiers get **red-stamped**; Claude Code card races **195M→220M** counter; Step Finance **$40M → $0 drains** |
| Stat card | counter ticking toward **3B pages/month** (tabular font, EaseOut) |
| Turn | boundary line **draws itself** (stroke-dashoffset draw-on) between montage and live catch — the tool boundary, literal |
| Live takes ×4 | `Clip` ranges, pane cropped to row/band; lower-thirds via the documented recipe citing source + date |
| `chain ✓` beat | chain link **closes** (draw-on) as verify lands |
| Tag | four badge stamps + wordmark; caret hold, no exit motion |

## QA loop (agent-verifiable, run per scene)

`inspect` (missing fonts/text-clips/panics per-scene) → `strip` contact
sheet → `frame scene@50%` at key moments → `onion` on every transition →
`audio analyze` (LUFS/peak/clipping + waveform PNG) → `render --draft`
(~1 s/scene). Human `preview` window gate before final render.

## Checklist before shipping

- [ ] First frame non-blank; hook inside 1.5 s
- [ ] Nothing below 28 px; no line >8 words; safe margins respected
- [ ] Every text readable (3 w/s + 1 s after settle)
- [ ] One eye-pull per moment; staggers not simultaneity
- [ ] `#E5523D` only threat, green only verify/receipt, `#8e4ec6` only edges
- [ ] Transitions: no empty/flash frames (checked `end`+`first`+`onion`)
- [ ] `inspect` clean; LUFS in range; no clipping
- [ ] No-slop test: swap text → is it still OUR film? (yes = footage carries it)

## Phase plan

0. Soundtrack + VO script → beat grid → timings locked *(in progress)*
1. Spike: `Clip` footage + lower-third over pane take, `render --draft`
2. Produced scenes per the table above
3. Assemble; QA loop; two scene-graph configs → `final-80s.mp4` + `final-40s-x.mp4`
4. Human preview → render → X post (Tue–Thu ~10am ET, 15–20 accounts
   primed in first hour, link in reply) + Typeform

## Setup notes

- `npx skills add https://fframes.studio` installs the agent skill;
  project scaffold via `scripts/new-video.sh` (reinstalls latest).
- macOS deps: `brew install pkg-config ffmpeg x264 x265 opus nasm ninja`.
- Skia GPU (Metal) backend ~10× CPU; static SVG subtrees are
  compile-time cached — keep `{expressions}` out of static content.
- Beta (`v1.0.0-beta.7`): footage `Clip` path is the one to spike first.

## Build state (Nov 5 — phase 1 spike complete)

`demo-video/hermes/montage/` — fframes project, 5 scenes live, all verified:
Montage (incident cards + dimmed ledger + red progress), StatCard (0→3B
counter), Turn (draw-on boundary line), LiveTake (footage + lower-third —
**Clip path proven end-to-end with placeholder mp4**), Tag (badge stamps +
caret). `inspect` clean, `timeline` 31 s/930 fr, `render --draft` 3.2 s →
valid h264.

### Gotchas hit (needed for any rebuild)

- **fframes 1.4.x dep skew**: `fframes-media`/`fframes-media-dir-macro` must
  be pinned `=1.4.0` in `[dependencies]` — 1.4.1 broke `Subtitles`/`usvgr`
  compat against `fframes 1.4.0`.
- **Video files are never embedded** — `include_media_dir!` takes
  audio/images/fonts/vtt only and *panics* on mp4. Footage resolves by path
  via a second provider: `CombinedMediaProvider::from([&embedded, &extra])`
  where `extra = DynamicMediaProvider::new(.., videos, ..)` with
  `VideoMedia { path: "footage/take.mp4" }`. Put takes in `footage/`, not `media/`.
- **Scenes must return a rooted `<svg>`** — bare `<g>` fragments →
  `NoRootNode` on inspect.
- **`timeline!` can't capture vars** — use manual `ease_out(t)` math for
  data-dependent timing (card entries), `&timeline!(...)` for literals.
- **Fonts: ttf only** — woff2 rejected; `fontTools` converts (`flavor=None`).
- **Zero-size rects rejected** — floor widths at 0.5. Unicode `▌` not in
  Satoshi — draw carets as `<rect>`.

### Next (blocked on assets, not code)

1. Record the 4 live takes per SHOTLIST → `footage/` (swap names in
   `videos` map + duplicate LiveTake scene per incident lower-third).
2. Soundtrack pick → beat grid → lock scene `duration`s + `overlap`s to it.
3. VO via narrate.mjs → `AudioMap` with ducking (audio.md recipe).
4. `render --draft` loop → human `preview` → `render` ×2 cuts.
