import assert from "node:assert/strict";
import { mkdtemp, readFile, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { readConfig, resolvedSettings, writeConfig } from "../src/config.mjs";

test("writes and reads config without exposing it to other Unix users", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "knot-agent-kit-"));
  const file = path.join(directory, "nested", "config.json");
  await writeConfig({ token: "secret", checkpoint: "42" }, file);

  assert.deepEqual(await readConfig(file), { token: "secret", checkpoint: "42" });
  assert.equal(JSON.parse(await readFile(file, "utf8")).token, "secret");
  if (process.platform !== "win32") assert.equal((await stat(file)).mode & 0o777, 0o600);
});

test("environment overrides saved settings", () => {
  const settings = resolvedSettings(
    { baseUrl: "https://saved.test/", token: "saved" },
    { KNOT_BASE_URL: "https://env.test/", KNOT_AGENT_TOKEN: "env" },
  );
  assert.equal(settings.baseUrl, "https://env.test");
  assert.equal(settings.token, "env");
});
