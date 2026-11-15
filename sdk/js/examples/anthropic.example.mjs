// Anthropic SDK via the Elcaro Gateway — tool_result blocks are scanned
// by default (§2.4).
//
//   npm i @anthropic-ai/sdk
//   ELCARO_API_KEY=elk_… node anthropic.example.mjs
import { ElcaroAnthropic } from "@elcaro/sdk/anthropic";

const client = new ElcaroAnthropic({
  upstreamKey: process.env.ANTHROPIC_API_KEY,
});

const res = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 256,
  messages: [
    {
      role: "user",
      content: [
        { type: "tool_result", tool_use_id: "toolu_1", content: "<retrieved email>" },
        { type: "text", text: "What does this email ask me to do?" },
      ],
    },
  ],
});

console.log(res.content);
