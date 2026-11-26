# @elcaro/sdk

Thin clients for the [Elcaro Gateway](https://gateway.elcaro.trustfall.xyz) —
drop-in wrappers for `openai`, `@anthropic-ai/sdk`, and the Vercel AI SDK.
The integration is a base-URL swap plus two headers; these wrappers exist
so you never hand-roll header names.

> **Not published to npm yet.** The recommended path is the zero-dependency
> swap below — the stock SDK with a `baseURL` and one header. Use this package
> only if you build it from source (`npm ci && npm run build`) or it gets
> published later.

## Zero-dependency path (recommended)

```ts
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.SERV_API_KEY, // the upstream credential
  baseURL: "https://gateway.elcaro.trustfall.xyz/v1", // note the /v1
  defaultHeaders: {
    "x-elcaro-key": process.env.ELCARO_API_KEY, // elk_… from /keys
  },
});
```

The key's `upstream` must match the credential: `serv` keys forward to SERV,
`openai` to OpenAI, `anthropic` to Anthropic. Pick the upstream when minting at
<https://elcaro.trustfall.xyz/keys>.

Anthropic uses the version-free root — its SDK appends `/v1/messages` itself:

```ts
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY, // rides x-api-key
  baseURL: "https://gateway.elcaro.trustfall.xyz",
  defaultHeaders: { "x-elcaro-key": process.env.ELCARO_API_KEY },
});
```

## Wrapper path (build from source)

```bash
git clone https://github.com/…/elcaro && cd elcaro/sdk/js
npm ci && npm run build
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
