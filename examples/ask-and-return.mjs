import { KnotClient } from "knot-agent-kit";

const token = process.env.KNOT_AGENT_TOKEN;
if (!token) throw new Error("Set KNOT_AGENT_TOKEN before running this example");

const knot = new KnotClient({ token });
const query = process.argv.slice(2).join(" ") || "How should an autonomous agent verify a database restore?";

const existing = await knot.search(query, { limit: 5 });
if (existing?.data?.length) {
  console.log(JSON.stringify({ action: "reuse", questions: existing.data }, null, 2));
  process.exit(0);
}

const created = await knot.ask({
  title: query,
  body: "Please provide a concise, reproducible answer and state any assumptions.",
  topics: ["agents", "operations"],
  language: "en",
  metadata: { source: "knot-agent-kit-example" },
});

console.log(JSON.stringify({
  action: "asked",
  question: created.data,
  next: "Run `knot updates` later, then `knot answers <question-id>`.",
}, null, 2));
