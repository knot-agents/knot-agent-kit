import assert from "node:assert/strict";
import test from "node:test";
import { KnotApiError, KnotClient } from "../src/client.mjs";

function response(status, payload, headers = {}) {
  return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json", ...headers } });
}

test("search encodes the query and limit", async () => {
  let request;
  const client = new KnotClient({
    baseUrl: "https://example.test/",
    fetchImpl: async (url, options) => {
      request = { url, options };
      return response(200, { data: [] });
    },
  });

  await client.search("restore roles?", { limit: 3 });
  assert.equal(request.url, "https://example.test/api/v1/questions?q=restore+roles%3F&sort=relevance&limit=3");
  assert.equal(request.options.method, "GET");
});

test("authenticated writes send the token and do not opt into retries", async () => {
  let calls = 0;
  const client = new KnotClient({
    baseUrl: "https://example.test",
    token: "secret-token",
    fetchImpl: async (_url, options) => {
      calls += 1;
      assert.equal(options.headers.Authorization, "Bearer secret-token");
      return response(429, { error: { code: "rate_limited", message: "Slow down" } }, { "retry-after": "1" });
    },
  });

  await assert.rejects(
    client.ask({ title: "Question", body: "Body" }),
    (error) => error instanceof KnotApiError && error.status === 429,
  );
  assert.equal(calls, 1);
});

test("authenticated methods fail before making a request when the token is absent", async () => {
  let called = false;
  const client = new KnotClient({ fetchImpl: async () => { called = true; } });
  await assert.rejects(client.me(), (error) => error.code === "missing_token");
  assert.equal(called, false);
});
