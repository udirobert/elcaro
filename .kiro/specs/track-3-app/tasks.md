# Track 3 — App: Tasks

## Status key
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1 — Next.js scaffolding (complete by Aug 10)

- [ ] **1.1 Initialise the Next.js project**
  ```bash
  cd app
  npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir
  ```
  - App Router, TypeScript strict, Tailwind CSS, ESLint
  - Verify `npm run dev` starts on port 3000
  - Add `.env.local.example` with `ELCARO_MINER_URL=http://localhost:8000`

- [ ] **1.2 Configure Tailwind for dark mode + risk colours**
  - Dark mode: `class` strategy (default dark, toggle later)
  - Custom colours: `safe` (emerald), `low` (blue), `suspicious` (amber), `dangerous` (red)
  - Add Geist or Inter font via `next/font`

- [ ] **1.3 Set up project structure**
  - Create directories: `src/components/`, `src/components/ui/`, `src/lib/`
  - Create `src/lib/constants.ts` with example payloads and content types
  - Create `src/lib/api.ts` with typed fetch wrapper

- [ ] **1.4 Create the API proxy route**
  - `src/app/api/scan/route.ts`
  - Proxy POST to `ELCARO_MINER_URL/scan`
  - Handle errors gracefully (return structured error JSON)
  - Test: `curl -X POST http://localhost:3000/api/scan -H "Content-Type: application/json" -d '{"content": "SYSTEM: test", "content_type": "email"}'`

---

## Phase 2 — Core scan page (complete by Aug 13)

- [ ] **2.1 Build the scan form component**
  - `src/components/scan-form.tsx`
  - Textarea with placeholder text
  - Content type dropdown (all 6 types)
  - Scan button with loading state
  - Client Component (`"use client"`)

- [ ] **2.2 Build the result display components**
  - `src/components/risk-badge.tsx` — numeric score + colour-coded badge + visual bar
  - `src/components/technique-pill.tsx` — technique class as a coloured pill
  - `src/components/indicator-card.tsx` — expandable card with technique name, confidence %, matched text, explanation
  - `src/components/scan-result.tsx` — assembles all result components

- [ ] **2.3 Build the example buttons**
  - `src/components/example-buttons.tsx`
  - At least 3 injection examples (authority, delimiter, conditional) + 2 clean examples
  - Clicking pre-fills the textarea and selects the content type

- [ ] **2.4 Build the loading state**
  - Animated thinking orb (CSS-only or from orbs.jakubantalik.com)
  - Appears during scan, disappears on result

- [ ] **2.5 Assemble the scan page**
  - `src/app/scan/page.tsx`
  - Layout: form top, results below (appear after scan)
  - Responsive: single column on mobile, wider on desktop
  - Test end-to-end with local miner running

---

## Phase 3 — Landing page (complete by Aug 16)

- [ ] **3.1 Build the hero section**
  - Headline: what Elcaro does (one sentence)
  - Subheading: why it matters (one sentence)
  - CTA button → `/scan`
  - Optional: subtle WebGL background effect (canvasui.dev)

- [ ] **3.2 Build the "how it works" section**
  - 3 steps: 1. Paste content, 2. Elcaro scans, 3. Safe or quarantined
  - Visual: icons or simple illustrations

- [ ] **3.3 Build the technique showcase**
  - The A–F taxonomy as a visual grid/table
  - Each class with its name and a one-line description

- [ ] **3.4 Set up Open Graph metadata**
  - Title, description, og:image
  - Create or generate an OG image (1200×630)
  - Test with Twitter Card Validator / opengraph.xyz

- [ ] **3.5 Assemble the landing page**
  - `src/app/page.tsx` (Server Component)
  - Hero → How it works → Technique showcase → CTA footer
  - Responsive and fast (no client JS on initial load)

---

## Phase 4 — Polish + deploy (complete by Aug 19)

- [ ] **4.1 Add the border beam effect to result card**
  - Beam colour changes with risk level
  - Subtle — accent, not distraction

- [ ] **4.2 Add responsive tweaks**
  - Test on mobile viewport (375px)
  - Ensure textarea, results, and examples all work on small screens

- [ ] **4.3 Add ESLint + Prettier config**
  - Run `npx eslint . --fix`
  - Add to pre-commit if desired

- [ ] **4.4 Deploy to Vercel**
  - Connect GitHub repo
  - Set `ELCARO_MINER_URL` environment variable (points to deployed Python miner)
  - Verify: visit deployed URL, scan an injection payload, see results

- [ ] **4.5 Smoke test deployed app**
  - Injection payload → quarantined, red badge
  - Clean payload → safe, green badge
  - Check Python miner logs → requests coming in from Vercel

---

## Phase 5 — Kiro submission (complete by Aug 23)

- [ ] **5.1 Record demo video**
  - Show the landing page
  - Navigate to /scan, paste an injection payload, show the result
  - Paste a clean payload, show it passing
  - Show the `.kiro/` directory and explain spec-driven development
  - Show the test suite running
  - Upload to YouTube (unlisted is fine)

- [ ] **5.2 Submit to Kiro hackathon**
  - Fill out Google Form
  - Attach: repo URL, demo video URL, project details
  - Verify all submission requirements met

---

## Phase 6 — Telegraph Track 3 (complete by Sep 7)

- [ ] **6.1 Post Track 3 announcement on X**
  - Lead with the demo URL
  - Show a GIF/screenshot of detection in action
  - Tag Telegraph Protocol

- [ ] **6.2 Drive adoption**
  - Post in Telegraph Discord — offer the middleware to other teams
  - Post integration example showing 5-line Python snippet
  - Track request volume on the miner

- [ ] **6.3 Add stats banner (if time)**
  - Show total scans, injections caught, average response time
  - Fetched from a `/api/stats` route calling the miner

---

## Completion criteria

### Kiro hackathon (Aug 23):
- [ ] Landing page live on Vercel
- [ ] Scan page functional with real detection results
- [ ] Open Graph metadata set (good link previews on X)
- [ ] Demo video recorded and uploaded
- [ ] Google Form submitted

### Telegraph Track 3 (Sep 7):
- [ ] All requests route through the live Track 1 miner (not local engine)
- [ ] At least one X post published with the demo link
- [ ] At least one other team has seen/used the integration
- [ ] Request volume visible in miner logs
