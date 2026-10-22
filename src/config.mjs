import { chmod, mkdir, readFile, rename, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";

export function defaultConfigPath(env = process.env, platform = process.platform) {
  if (env.KNOT_CONFIG_FILE) return path.resolve(env.KNOT_CONFIG_FILE);
  if (platform === "win32") {
    const root = env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
    return path.join(root, "Knot", "agent-kit.json");
  }
  const root = env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
  return path.join(root, "knot", "agent-kit.json");
}

export async function readConfig(file = defaultConfigPath()) {
  try {
    const parsed = JSON.parse(await readFile(file, "utf8"));
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    if (error?.code === "ENOENT") return {};
    throw error;
  }
}

export async function writeConfig(config, file = defaultConfigPath()) {
  await mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${process.pid}.${crypto.randomUUID()}.tmp`;
  await writeFile(temporary, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
  if (process.platform !== "win32") await chmod(temporary, 0o600);
  await rename(temporary, file);
  if (process.platform !== "win32") await chmod(file, 0o600);
}

export function resolvedSettings(config = {}, env = process.env) {
  return {
    baseUrl: String(env.KNOT_BASE_URL || config.baseUrl || "https://knot.antisla.sh").replace(/\/$/, ""),
    token: env.KNOT_AGENT_TOKEN || config.token || null,
    checkpoint: config.checkpoint || null,
    agent: config.agent || null,
  };
}
