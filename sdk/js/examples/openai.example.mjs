// OpenAI SDK via the Elcaro Gateway — the only change from a stock
// `new OpenAI()` is the constructor name and the two keys.
//
//   npm i openai
//   ELCARO_API_KEY=elk_… node openai.example.mjs
import { ElcaroOpenAI } from "@elcaro/sdk/openai";
import { untrusted, verdictFromHeaders } from "@elcaro/sdk";

const client = new ElcaroOpenAI({
  // elcaroKey defaults to process.env.ELCARO_API_KEY
  upstreamKey: process.env.OPENAI_API_KEY,
});

// A tool result carrying third-party content is scanned by default;
// `untrusted()` marks anything else (§2.4).
const res = await client.chat.completions.create(
  {
    model: "gpt-5",
    messages: [
      { role: "user", content: "Summarize the doc I fetched." },
      { role: "tool", tool_call_id: "call_1", content: "<retrieved doc>" },
      {
        role: "user",
        content: [{ type: "text", text: "And this part:" }, untrusted("<pasted content>")],
      },
    ],
  },
  // Response headers carry the §2.7 verdict metadata.
  { withResponse: true },
);

console.log(res.data.choices[0].message.content);
console.log(verdictFromHeaders(res.response.headers));
