# Chrome Web Store submission — Elcaro IPI Guard

Everything the CWS listing form asks for, drafted so submission is a
copy-paste exercise. Items that still need owner action are marked **[owner]**.

## Listing copy

**Name:** Elcaro IPI Guard

**Summary (132 chars max):**
```
Scan the open Gmail message for indirect prompt injection — hidden instructions aimed at your AI agent — before you act on it.
```

**Description:**
```
Elcaro IPI Guard scans the email you're reading for indirect prompt injection: hidden instructions embedded in otherwise normal-looking messages, written to hijack an AI agent that reads them.

One click on the Scan button in the Gmail toolbar (or ⌘⇧S / Alt+S) gives you:

• SAFE / CAUTION / BLOCK — a verdict, not just a score
• The injection techniques that fired, named plainly
• A one-line instruction on what to do next
• The scan's risk score with a proportional meter

Why this exists: agents that read email, browse the web, or process documents can be steered by instructions hidden in that content — to forward data, change payment details, or bypass their own safeguards. You can't see these instructions by reading the message as a human; they are written for the model, not for you. Elcaro reads the way the model reads.

Privacy, in one paragraph: the message text you scan is sent to Elcaro's scan service over HTTPS, processed, and never stored — scan history lives only in this browser, in chrome.storage.local, and you can erase it from the popup at any time. No account. No tracking. No analytics. No ads.

Elcaro is open source: github.com/udirobert/elcaro
```

**Category:** Productivity
**Language:** English

## Permission justifications (required per permission/host)

**`storage`**
```
Keeps your scan history and preferences (rail choice, first-run state) on
your own machine using chrome.storage.local. Nothing is sent to us — the
history never leaves the browser and can be erased from the extension popup.
```

**Host permission: `https://elcaro.trustfall.xyz/*`**
```
This is Elcaro's own scan service. When you click Scan, the open message's
text is sent here over HTTPS, analyzed for injection techniques, and the
verdict is returned. The text is processed in memory and never stored,
logged, or shared.
```

**Host permission: `https://devnode.telegraphprotocol.com/*`**
```
Used only by the optional "direct" developer rail to reach the Telegraph
network's miner gateway. The default Engine rail does not use it. No user
data is sent here unless the user explicitly switches rails in the popup.
```

**Host permission: `https://mail.google.com/*` (content script)**
```
The extension reads the text of the message you explicitly choose to scan,
and only when you click Scan or press the shortcut. It does not read your
inbox, list mail, or scan in the background.
```

**Remote code:** none — no remotely hosted code, all logic ships in the package.

## Privacy practices answers (data collection form)

| Question | Answer |
|---|---|
| Collects user data? | **No** — with one nuance below |
| Personally identifiable info | Not collected |
| Health/financial/location/etc | Not collected |
| Personal communications | **Message content is transmitted for scanning, not stored** — declare as: "transmitted to provide the service, not retained" |

CWS wording for the single-purpose + data-use disclosure:

```
Single purpose: scanning open Gmail messages for indirect prompt injection.

Data use: the text of a message you explicitly scan is transmitted over HTTPS
to the scan service for analysis and is not stored, sold, or used for any
other purpose. Scan history is stored only locally in your browser and is
erasable. The extension does not use or transfer data for purposes unrelated
to its single purpose, does not use data for creditworthiness or lending,
and does not sell user data.
```

## Privacy policy (hosted)

Needs a public URL. **[owner]** — suggested path: publish at
`elcaro.trustfall.xyz/privacy-extension` or reuse a privacy section on the
site. Draft text is below — host it anywhere public and paste the URL into
the listing.

```
Elcaro IPI Guard — Privacy Policy

What we receive. When you click Scan (or press the shortcut), the text of the
Gmail message currently open in your browser is sent over HTTPS to the Elcaro
scan service (elcaro.trustfall.xyz) for analysis.

What we do with it. The text is analyzed in memory for indirect prompt
injection techniques and the verdict is returned to your browser. Message
content is never written to disk, logged, or stored on the server.

What we never do. We do not read your inbox. We do not scan in the
background. We do not sell, share, or mine message content. There is no
account, no tracking, no analytics, and no advertising.

What stays on your machine. Scan history (verdict band, score, date) is kept
in your browser's local storage so the popup can show your day at a glance.
It never leaves your browser and can be erased at any time from the popup
("Clear history").

Contact. github.com/udirobert/elcaro — issues welcome.
```

## Pre-submission checklist

- [x] Icons 16/32/48/128 (violet tile, white "e")
- [x] Minimal permissions — `storage` only
- [x] aria-live + focus management on the overlay
- [ ] Version bump to 1.0.0 in manifest.json **[do at submission]**
- [ ] Privacy policy hosted at a public URL **[owner]**
- [ ] 1280×800 screenshots ×1–3 (scan flow: SAFE example + BLOCK example) **[owner — needs a real Gmail account]**
- [ ] 128×128 store icon = icons/icon-128.png ✓
- [ ] Test account / instructions for reviewers: "Open any email in Gmail,
      click Scan in the thread toolbar. A demo scan is possible on any
      message — no fixtures needed."
- [ ] Zip the directory for upload: `cd app/extension && zip -r gmail-scan.zip gmail-scan -x '*.md'`
      (exclude *.md docs — README/CWS are repo material, not runtime)

## Known reviewer-friction risks

1. **Host permission to devnode.telegraphprotocol.com** may draw scrutiny as
   a third-party endpoint. Mitigation: it is documented above and in the
   listing as dev-only. If rejected or questioned, consider removing the
   direct rail from the shipping build entirely — it is a development
   fallback, and dropping it deletes one justification.
2. **"Reads your email" sensitivity.** The justifications above lean on the
   explicit user-triggered scan. Do not add automatic scanning — it would
   flip the privacy story and likely sink review.
3. **Payment-adjacent claims.** Scans are paid per request by Elcaro's
   service, not the user — the listing copy deliberately never mentions
   money. Keep it that way.
