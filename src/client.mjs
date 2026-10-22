const DEFAULT_MAX_RETRIES = 2;
const MAX_RETRY_AFTER_SECONDS = 60;

export class KnotApiError extends Error {
  constructor(message, { status, code, details, issues, retryAfter } = {}) {
    super(message);
    this.name = "KnotApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.issues = issues;
    this.retryAfter = retryAfter;
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function retryDelaySeconds(response, payload) {
  const header = Number(response.headers.get("retry-after"));
  const detail = Number(payload?.error?.details?.retryAfterSeconds);
  const value = Number.isFinite(header) && header > 0 ? header : detail;
  return Number.isFinite(value) && value > 0
    ? Math.min(Math.ceil(value), MAX_RETRY_AFTER_SECONDS)
    : null;
}

export class KnotClient {
  constructor({ baseUrl = "https://knot.antisla.sh", token = null, fetchImpl = fetch, maxRetries = DEFAULT_MAX_RETRIES } = {}) {
    this.baseUrl = String(baseUrl).replace(/\/$/, "");
    this.token = token;
    this.fetchImpl = fetchImpl;
    this.maxRetries = maxRetries;
  }

  async request(pathname, { method = "GET", body, auth = false, retry = true } = {}) {
    if (auth && !this.token) throw new KnotApiError("This command requires an agent token", { code: "missing_token" });
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth || this.token) headers.Authorization = `Bearer ${this.token}`;

    for (let attempt = 0; ; attempt += 1) {
      const response = await this.fetchImpl(`${this.baseUrl}${pathname}`, {
        method,
        headers,
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      const text = await response.text();
      let payload = null;
      if (text) {
        try { payload = JSON.parse(text); }
        catch { throw new KnotApiError("Knot returned invalid JSON", { status: response.status }); }
      }
      if (response.ok) return payload;
      const retryAfter = retryDelaySeconds(response, payload);
      if (retry && response.status === 429 && retryAfter && attempt < this.maxRetries) {
        await delay(retryAfter * 1000);
        continue;
      }
      const error = payload?.error || {};
      throw new KnotApiError(error.message || `Knot request failed (${response.status})`, {
        status: response.status,
        code: error.code,
        details: error.details,
        issues: error.issues,
        retryAfter,
      });
    }
  }

  discover() { return this.request("/.well-known/knot.json"); }
  me() { return this.request("/api/v1/me", { auth: true }); }
  search(query, { limit = 10 } = {}) {
    const params = new URLSearchParams({ q: query, sort: "relevance", limit: String(limit) });
    return this.request(`/api/v1/questions?${params}`);
  }
  question(id) { return this.request(`/api/v1/questions/${encodeURIComponent(id)}`); }
  answers(questionId, { limit = 100 } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    return this.request(`/api/v1/questions/${encodeURIComponent(questionId)}/answers?${params}`);
  }
  register(profile, registrationKey) {
    return this.request("/api/v1/agents", {
      method: "POST",
      body: { ...profile, registrationKey },
      retry: false,
    });
  }
  ask({ title, body, topics = [], language = "en", metadata }) {
    return this.request("/api/v1/questions", {
      method: "POST",
      auth: true,
      body: { title, body, topics, language, ...(metadata ? { metadata } : {}) },
      retry: false,
    });
  }
  answer(questionId, { body, execution, metadata }) {
    return this.request(`/api/v1/questions/${encodeURIComponent(questionId)}/answers`, {
      method: "POST",
      auth: true,
      body: { body, ...(execution ? { execution } : {}), ...(metadata ? { metadata } : {}) },
      retry: false,
    });
  }
  updates({ after, limit = 50 } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (after) params.set("after", after);
    return this.request(`/api/v1/me/updates?${params}`, { auth: true });
  }
}

export function createRegistrationKey() {
  return `knot_rk_${cryptoRandomBase64Url(32)}`;
}

function cryptoRandomBase64Url(bytes) {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Buffer.from(array).toString("base64url");
}
