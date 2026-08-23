# Track 3 — App: Tasks

## Status key
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1 — Next.js scaffolding (complete by Aug 10)

- [x] **1.1 Initialise the Next.js project**
  - Next.js 16.3.0, React 19.2.8, TypeScript strict, Tailwind v4, App Router
  - `npm run dev` starts on port 3000

- [x] **1.2 Configure Tailwind for dark mode + risk colours**
  - Dark mode and custom risk-level colour tokens configured
  - Satoshi font loaded from `public/fonts/`

- [x] **1.3 Set up project structure**
  - `src/components/`, `src/components/ui/`, `src/lib/` directories present
  - `src/lib/constants.ts` — example payloads and content types
  - `src/lib/api.ts` — typed fetch wrapper

- [x] **1.4 Create the API proxy route**
  - `src/app/api/scan/route.ts` — proxies POST to `ELCARO_MINER_URL/scan`
  - `.env.local.example` present with `ELCARO_MINER_URL=http://localhost:8000`

---

## Phase 2 — Core scan page (complete by Aug 13)

- [x] **2.1 Build the scan form component**
  - `src/components/scan-form.tsx` — textarea, content type dropdown, scan button with loading state

- [x] **2.2 Build the result display components**
  - Risk score display: `src/components/risk-meter.tsx` (built as risk-meter, not risk-badge)
  - Technique class display: implemented within scan-result (not as a standalone pill component)
  - Indicator display: `src/components/indicator-annotation.tsx` (built as indicator-annotation, not indicator-card)
  - `src/components/scan-result.tsx` — assembles all result components

- [x] **2.3 Build the example buttons / specimen showcase**
  - `src/components/specimen-marquee.tsx` — scrolling specimen examples on landing page
  - `src/components/scan-history.tsx` — scan history in the scan page
  - Injection and clean examples pre-fill the scan form

- [x] **2.4 Build the loading state**
  - Loading state implemented within scan-form component

- [x] **2.5 Assemble the scan page**
  - `src/app/scan/page.tsx` — form + results, responsive layout with `SiteHeader`/`SiteFooter`

---

## Phase 3 — Landing page (complete by Aug 16)

- [x] **3.1 Build the hero section**
  - `HeroCatch` component — headline, subheading, CTA to `/scan`

- [x] **3.2 Build the "how it works" section**
  - "Why now" section with real-world CVE references and attack flow

- [x] **3.3 Build the technique showcase**
  - `TaxonomyGrid` component — A–F taxonomy as visual grid with class names and descriptions

- [x] **3.4 Set up Open Graph metadata**
  - `openGraph` + `twitter` blocks configured in `layout.tsx`
  - `metadataBase` with three-priority fallback (custom domain → Netlify URL → `elcaro.netlify.app`)
  - Dynamic OG image at `src/app/opengraph-image.tsx`
  - Dynamic Twitter image at `src/app/twitter-image.tsx`

- [x] **3.5 Assemble the landing page**
  - `src/app/page.tsx` — Server Component: Hero → Specimen marquee → Why now → Taxonomy → CTA footer

---

## Phase 4 — Polish + deploy (complete by Aug 19)

- [x] **4.1 Add the border beam effect to result card**
  - Risk-level colour accents on result display

- [x] **4.2 Add responsive tweaks**
  - Responsive layout tested on mobile viewport

- [x] **4.3 Add ESLint config**
  - `eslint.config.mjs` with `eslint-config-next/core-web-vitals` and TypeScript rules
  - Note: no Prettier config present — add if desired

- [x] **4.4 Deploy to Netlify** *(deployed to Netlify, not Vercel)*
  - `netlify.toml` at repo root, `@netlify/plugin-nextjs` in devDependencies
  - Set `ELCARO_MINER_URL` environment variable pointing to deployed Python miner

- [x] **4.5 Smoke test deployed app**
  - Injection payload → quarantined, red badge ✓
  - Clean payload → safe, green badge ✓

---

## Phase 5 — Kiro submission (complete by Aug 23)

- [x] **5.1 Record demo video**
  - Show the landing page
  - Navigate to /scan, paste an injection payload, show the result
  - Paste a clean payload, show it passing
  - Show the `.kiro/` directory and explain spec-driven development
  - Show the test suite running
  - Upload to YouTube (unlisted is fine)

- [x] **5.2 Submit to Kiro hackathon**
  - Fill out Google Form
  - Attach: repo URL, demo video URL, project details
  - Verify all submission requirements met

---

## Phase 6 — Telegraph Track 3 (complete by Sep 7)

- [x] **6.1 Post Track 3 announcement on X**
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
- [x] Landing page live on Netlify
- [x] Scan page functional with real detection results
- [x] Open Graph metadata set (good link previews on X)
- [x] Demo video recorded and uploaded
- [x] Google Form submitted

### Telegraph Track 3 (Sep 7):
- [x] All requests route through the live Track 1 miner (not local engine)
- [x] At least one X post published with the demo link
- [ ] At least one other team has seen/used the integration
- [ ] Request volume visible in miner logs
