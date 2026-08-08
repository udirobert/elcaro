# Track 3 — App: Design

## Vision

Elcaro's frontend is not a hackathon demo — it's the product surface for a
real content safety service. The initial build serves two hackathon submissions
(Kiro by Aug 23, Telegraph by Sep 7), but the architecture must support
evolution into a production SaaS tool with:

- User accounts and API key management
- A dashboard showing scan history, detection trends, and false-positive tuning
- Developer documentation and integration guides
- Batch scanning and webhook notifications
- A public-facing marketing/landing page

## Stack decision: Next.js (App Router) + Tailwind CSS

| Criterion | Decision |
|---|---|
| Framework | Next.js 14+ (App Router, React Server Components) |
| Styling | Tailwind CSS 4 |
| Deployment | Vercel (zero-config, free tier, edge functions) |
| API integration | Server Actions + Route Handlers calling the Python miner |
| Component patterns | React components from aicss.dev, beautiful-ui, canvasui.dev |
| State management | React hooks (useState/useReducer) — no Redux, not needed yet |
| Auth (future) | NextAuth.js or Clerk when user accounts are needed |
| Analytics (future) | Vercel Analytics or PostHog |

### Why Next.js over Astro

- The UI resources (aicss.dev, beautiful-ui, canvasui.dev) are React-native
- Next.js App Router gives us Server Components (fast initial load) + Client Components (rich interactivity)
- API Route Handlers let the frontend proxy requests to the Python miner — no CORS issues in production
- Vercel deployment is zero-config and gives us preview deploys on every PR
- The path to adding auth, dashboards, and billing is well-trodden in Next.js

### Why not merge the Python backend into Node

The Python detection engine is the core IP — regex patterns, scoring logic,
the detector architecture. It stays in Python because:
- The detectors use Python's `re` module extensively (rewriting in JS gains nothing)
- The eval script (Track 2) depends on the Python engine for validation
- The Telegraph miner protocol expects the Python API
- Separation of concerns: the frontend is a presentation/UX layer, the engine is a compute layer

The frontend calls the Python miner via HTTP (same as any other consumer).
In development, the miner runs on `localhost:8000` and the Next.js dev server
runs on `localhost:3000`. In production, the miner is deployed separately
(VPS) and the frontend calls it via environment variable.

## Directory structure

```
app/
├── web/                          # Next.js application (new)
│   ├── src/
│   │   ├── app/                  # App Router pages
│   │   │   ├── layout.tsx        # Root layout (dark theme, fonts, metadata)
│   │   │   ├── page.tsx          # Landing/hero page
│   │   │   ├── scan/
│   │   │   │   └── page.tsx      # Interactive scan page (the core demo)
│   │   │   ├── docs/
│   │   │   │   └── page.tsx      # Integration documentation (future)
│   │   │   └── api/
│   │   │       └── scan/
│   │   │           └── route.ts  # Route Handler proxying to Python miner
│   │   ├── components/
│   │   │   ├── scan-form.tsx     # Content input + type selector + scan button
│   │   │   ├── scan-result.tsx   # Risk score display, indicators, quarantine status
│   │   │   ├── risk-badge.tsx    # Colour-coded risk score badge
│   │   │   ├── indicator-card.tsx # Individual detection indicator
│   │   │   ├── technique-pill.tsx # Technique class badge
│   │   │   ├── example-buttons.tsx # Pre-loaded injection/clean examples
│   │   │   ├── thinking-orb.tsx  # Loading animation (from orbs.jakubantalik.com)
│   │   │   └── ui/              # Shared primitives (button, card, input, etc.)
│   │   ├── lib/
│   │   │   ├── api.ts           # Client-side fetch wrapper for /api/scan
│   │   │   └── constants.ts     # Example payloads, content types, etc.
│   │   └── styles/
│   │       └── globals.css       # Tailwind directives + custom properties
│   ├── public/
│   │   └── og-image.png          # Open Graph image for X/social sharing
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── .env.local.example        # ELCARO_MINER_URL=http://localhost:8000
├── middleware.py                  # Existing Python middleware (unchanged)
└── demo.py                       # Existing Python demo (unchanged)
```

## Page architecture

### Landing page (`/`)

The first thing anyone sees. Must answer three questions in 5 seconds:
1. What is this? → "Content safety scanning for AI agents"
2. Why do I care? → "Your agent is vulnerable to prompt injection"
3. What do I do? → CTA button → "Try a scan" (links to `/scan`)

Also serves as the social sharing destination when posting on X.
Good Open Graph metadata = good link previews = better engagement.

### Scan page (`/scan`)

The core interactive experience. Layout:

```
┌──────────────────────────────────────────────────────┐
│  [Content input textarea]                             │
│  [Content type dropdown]  [Scan button]              │
│                                                       │
│  [Example buttons: "Try injection" "Try clean"]      │
├──────────────────────────────────────────────────────┤
│  RESULTS (appears after scan)                        │
│                                                       │
│  ┌─ Risk Score ─────────────────────────────────┐    │
│  │  0.95  DANGEROUS  [authority_framing]         │    │
│  │  ████████████████████████████████░░░░░░░░░░  │    │
│  └───────────────────────────────────────────────┘    │
│                                                       │
│  ┌─ Indicators ─────────────────────────────────┐    │
│  │  ▸ authority:system_voice_marker (90%)        │    │
│  │    "SYSTEM:" in email content. Retrieved      │    │
│  │    content cannot contain legitimate system   │    │
│  │    instructions.                              │    │
│  │  ▸ authority:anti_confirmation (65%)          │    │
│  │    ...                                        │    │
│  └───────────────────────────────────────────────┘    │
│                                                       │
│  ┌─ Quarantine Decision ────────────────────────┐    │
│  │  🚫 Content would be QUARANTINED             │    │
│  │  Reason: Risk score 0.95 (dangerous)...      │    │
│  └───────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

### Docs page (`/docs`) — future

Integration guide with code examples in Python, TypeScript, and curl.
Shows how to use the middleware, call the API directly, or integrate via Telegraph.

## Visual design

### Theme
- Dark mode primary (security tool convention, looks good in demo videos)
- Light mode optional (user preference via `prefers-color-scheme`)
- Accent colour shifts with risk level:
  - Safe: emerald/green
  - Low: blue
  - Suspicious: amber
  - Dangerous: red

### Effects from linked resources
- **Thinking orb** (orbs.jakubantalik.com) — loading state while scan is in progress
- **Border beam** (beam.jakubantalik.com) — accent on the result card, colour matches risk level
- **Context cards** (beautiful-ui / aicss.dev patterns) — for displaying indicators
- **WebGL overlay** (canvasui.dev) — subtle background texture on the landing page hero

### Typography
- Mono font for matched text, code snippets, JSON
- Sans-serif for body text and headings
- System font stack for performance (Inter or Geist as web font if desired)

## API proxy pattern

The Next.js Route Handler at `/api/scan` proxies to the Python miner:

```typescript
// src/app/api/scan/route.ts
export async function POST(request: Request) {
  const body = await request.json();
  const minerUrl = process.env.ELCARO_MINER_URL || 'http://localhost:8000';

  const response = await fetch(`${minerUrl}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return Response.json(data);
}
```

This means:
- No CORS configuration needed (same-origin from the browser's perspective)
- The miner URL is never exposed to the client
- We can add rate limiting, caching, or auth at the proxy layer later
- In development: miner on :8000, Next.js on :3000, proxy handles the bridge

## Deployment architecture

```
┌─────────────┐         ┌──────────────────┐
│   Vercel    │ ──────▶ │    VPS           │
│  (Next.js)  │  HTTP   │  (Python miner)  │
│  app/web/   │         │  miner/api.py    │
└─────────────┘         └──────────────────┘
      │                          │
      │                          ▼
      │                  ┌──────────────┐
      ▼                  │  Telegraph   │
  End users              │  Network     │
  (browser)              └──────────────┘
```

- **Vercel**: hosts the Next.js frontend, free tier, automatic HTTPS, preview deploys
- **VPS**: hosts the Python miner API (Track 1), stable URL, HTTPS via reverse proxy (Caddy/nginx + Let's Encrypt)
- Connection: `ELCARO_MINER_URL` environment variable on Vercel points to the miner

## Evolution path (post-hackathon)

| Phase | Addition | Effort |
|---|---|---|
| v0.1 (hackathon) | Landing page + scan page + example buttons | This sprint |
| v0.2 | Batch scan, JSON/CSV export, shareable result links | 1 week |
| v0.3 | User accounts (NextAuth), API key generation, usage dashboard | 2 weeks |
| v0.4 | Integration docs page, SDK packages (npm + pip) | 1 week |
| v0.5 | Billing (Stripe), rate tiers, team accounts | 2 weeks |
| v1.0 | Production launch: custom domains, SLA, enterprise features | Ongoing |

## What NOT to change

The Python middleware (`app/middleware.py`) and demo (`app/demo.py`) remain
as-is. They're the library integration path for Python developers. The Next.js
app is the web UI path — they coexist, serving different audiences.

The Python miner API (`miner/api.py`) is the single source of truth for
detection. The Next.js app is a consumer, not a replacement. Never put
detection logic in the frontend.
