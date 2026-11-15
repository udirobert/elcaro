// Vercel AI SDK via the Elcaro Gateway — a provider factory, used like
// createOpenAI().
//
//   npm i ai @ai-sdk/openai
//   ELCARO_API_KEY=elk_… node vercel.example.mjs
import { createElcaroOpenAI } from "@elcaro/sdk/vercel";
import { generateText } from "ai";

const elcaro = createElcaroOpenAI({
  upstreamKey: process.env.OPENAI_API_KEY,
});

const { text } = await generateText({
  model: elcaro("gpt-5"),
  messages: [
    { role: "user", content: "Summarize:" },
    { role: "tool", toolCallId: "call_1", toolName: "fetch", content: "<retrieved doc>" },
  ],
});

console.log(text);
