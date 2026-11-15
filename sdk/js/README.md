# @elcaro/sdk

Thin clients for the [Elcaro Gateway](https://gateway.elcaro.trustfall.xyz) —
drop-in wrappers for `openai`, `@anthropic-ai/sdk`, and the Vercel AI SDK.
The integration is a base-URL swap plus two headers; these wrappers exist
so you never hand-roll header names.

```bash
npm i @elcaro/sdk openai          # or @anthropic-ai/sdk / ai + @ai-sdk/openai
```

```ts
import { ElcaroOpenAI } from "@elcaro/sdk/openai";

const client = new ElcaroOpenAI({
  elcaroKey: process.env.ELCARO_API_KEY, // elk_…
  upstreamKey: process.env.OPENAI_API_KEY, // forwarded untouched
});

// identical surface to `new OpenAI()` — scans run server-side
```

| Import | Wraps | Subpath |
|---|---|---|
| `ElcaroOpenAI` | `openai` | `@elcaro/sdk/openai` |
| `ElcaroAnthropic` | `@anthropic-ai/sdk` | `@elcaro/sdk/anthropic` |
| `createElcaroOpenAI` / `createElcaroAnthropic` | Vercel AI SDK | `@elcaro/sdk/vercel` |
| `untrusted`, `untrustedHeader`, `verdictFromHeaders` | helpers | `@elcaro/sdk` |

All peer SDKs are optional — install only the one you use.

- `untrusted(text)` marks a content part for scanning (gateway strips the
  marker before forwarding); `untrustedHeader(0, 2)` → `x-elcaro-untrusted`.
- `verdictFromHeaders(res.headers)` parses `x-elcaro-verdict` / `-action` /
  `-receipt` / `-cost-usdc` / `-incident` into a typed object.
- `baseURL` overrides for staging/self-hosts; `ELCARO_API_KEY` env supplies
  `elcaroKey`.

Peer deps are `devDependencies` here for typechecking; `dist/` is built —
run `npm run build` before `npm test`.
