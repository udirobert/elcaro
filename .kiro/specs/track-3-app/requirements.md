# Track 3 — App: Requirements

## Overview

The Elcaro app is the product surface for an IPI content safety service. It
provides a web interface for scanning content, viewing detection results, and
integrating Elcaro into agent workflows. Built with Next.js (App Router) and
deployed on Vercel, it calls the Python miner API (Track 1) for all detection
logic.

The app serves dual purposes:
1. **Hackathon submission** — a polished interactive demo for Kiro (Aug 23) and Telegraph Track 3 (~Aug 31)
2. **Product foundation** — the architecture supports evolution into a real SaaS tool with user accounts, dashboards, billing, and developer docs

## Functional requirements

### FR-1 Landing page (`/`)
- FR-1.1 The landing page MUST communicate what Elcaro does, why it matters, and how to try it within 5 seconds of loading
- FR-1.2 A clear CTA MUST link to the scan page (`/scan`)
- FR-1.3 Open Graph metadata MUST be set for good link previews on X/social (title, description, image)
- FR-1.4 The page MUST be server-rendered (RSC) for fast initial load and SEO

### FR-2 Scan page (`/scan`)
- FR-2.1 A text area MUST accept arbitrary content for scanning
- FR-2.2 A dropdown MUST allow selection of content type (email, search_result, webpage, document, code, chat_message)
- FR-2.3 A scan button MUST submit the content to `/api/scan` and display results
- FR-2.4 Results MUST display: risk score (numeric + visual bar), risk level (badge), flagged techniques (pill badges), and full indicators list
- FR-2.5 Each indicator MUST show: technique name, confidence percentage, matched text (highlighted), and explanation
- FR-2.6 A quarantine decision MUST be shown: "Safe to process" or "Would be quarantined" with the reason
- FR-2.7 "Try an example" buttons MUST pre-populate the textarea with at least 3 injection examples and 2 clean examples
- FR-2.8 A loading state MUST be shown during the scan request (animated orb or similar)
- FR-2.9 The scan page MUST work on mobile (responsive layout)

### FR-3 API proxy (`/api/scan`)
- FR-3.1 A Next.js Route Handler MUST proxy POST requests to the Python miner's `/scan` endpoint
- FR-3.2 The miner URL MUST be configured via `ELCARO_MINER_URL` environment variable (never exposed to the client)
- FR-3.3 The proxy MUST return the full `ScanResponse` JSON from the miner
- FR-3.4 On miner error (timeout, 5xx, unreachable), the proxy MUST return a structured error response (not crash)
- FR-3.5 The proxy MUST forward `content`, `content_type`, and `deep_analysis` fields from the client request

### FR-4 Visual design
- FR-4.1 Dark mode MUST be the default theme
- FR-4.2 Light mode SHOULD be supported via system preference detection
- FR-4.3 Risk level MUST be colour-coded: safe=green, low=blue, suspicious=amber, dangerous=red
- FR-4.4 The design MUST feel professional and security-oriented (not playful or casual)
- FR-4.5 Visual effects (orbs, beams, WebGL) SHOULD enhance without distracting

### FR-5 Development workflow
- FR-5.1 `npm run dev` (or equivalent) MUST start the Next.js dev server on port 3000
- FR-5.2 The dev server MUST work with the Python miner running on `localhost:8000`
- FR-5.3 A `.env.local.example` file MUST document all required environment variables
- FR-5.4 The project MUST use TypeScript with strict mode
- FR-5.5 ESLint and Prettier MUST be configured and pass before commits

### FR-6 Deployment
- FR-6.1 The app MUST deploy to Vercel with zero additional configuration beyond environment variables
- FR-6.2 `ELCARO_MINER_URL` MUST be the only required environment variable for production
- FR-6.3 The deployed app MUST serve over HTTPS
- FR-6.4 Build time MUST be under 60 seconds on Vercel

## Non-functional requirements

- NFR-1 First Contentful Paint MUST be under 1.5 seconds on a 4G connection
- NFR-2 The scan page MUST function without JavaScript for the initial render (progressive enhancement)
- NFR-3 The app MUST not store or log user-submitted content (privacy)
- NFR-4 All API calls from the browser go through `/api/scan` — the miner URL is never exposed client-side
- NFR-5 The app MUST be accessible (WCAG 2.1 AA): keyboard navigable, screen reader compatible, sufficient contrast
- NFR-6 The frontend MUST NOT contain any detection logic — all scanning is delegated to the Python miner

## Future requirements (not in scope for hackathon but architecture must not block)

- User accounts and API key management
- Scan history and usage dashboard
- Batch scanning endpoint
- Developer documentation page with code examples
- Billing/subscription management
- Team/organisation features
