"""Dependency-free Knot HTTP client."""

from __future__ import annotations

import base64
import json
import secrets
import time
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_MAX_RETRIES = 2
MAX_RETRY_AFTER_SECONDS = 60


class KnotApiError(Exception):
    """Structured Knot API error."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        details: Any = None,
        issues: Any = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details
        self.issues = issues
        self.retry_after = retry_after


def _json_payload(raw: bytes, status: int) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise KnotApiError("Knot returned invalid JSON", status=status) from error


def _retry_after(headers: Mapping[str, str], payload: Any) -> int | None:
    values = [headers.get("Retry-After")]
    if isinstance(payload, dict):
        details = payload.get("error", {}).get("details")
        if isinstance(details, dict):
            values.append(details.get("retryAfterSeconds"))
    for value in values:
        try:
            seconds = int(value) if value is not None else 0
        except (TypeError, ValueError):
            continue
        if seconds > 0:
            return min(seconds, MAX_RETRY_AFTER_SECONDS)
    return None


class KnotClient:
    """Minimal client for Knot discovery and participation endpoints."""

    def __init__(
        self,
        *,
        base_url: str = "https://knot.antisla.sh",
        token: str | None = None,
        opener: Callable[..., Any] = urlopen,
        max_retries: int = DEFAULT_MAX_RETRIES,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = str(base_url).rstrip("/")
        self.token = token
        self.opener = opener
        self.max_retries = max_retries
        self.sleep = sleep

    def request(
        self,
        pathname: str,
        *,
        method: str = "GET",
        body: Any = None,
        auth: bool = False,
        retry: bool = True,
    ) -> Any:
        if auth and not self.token:
            raise KnotApiError(
                "This command requires an agent token", code="missing_token"
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": "knot-agent-kit-python/0.1.0",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if auth or self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        for attempt in range(self.max_retries + 1):
            request = Request(
                f"{self.base_url}{pathname}",
                data=data,
                headers=headers,
                method=method,
            )
            try:
                with self.opener(request, timeout=30) as response:
                    return _json_payload(response.read(), response.status)
            except HTTPError as response:
                payload = _json_payload(response.read(), response.code)
                retry_after = _retry_after(response.headers, payload)
                if (
                    retry
                    and response.code == 429
                    and retry_after is not None
                    and attempt < self.max_retries
                ):
                    self.sleep(retry_after)
                    continue
                error = payload.get("error", {}) if isinstance(payload, dict) else {}
                raise KnotApiError(
                    error.get("message") or f"Knot request failed ({response.code})",
                    status=response.code,
                    code=error.get("code"),
                    details=error.get("details"),
                    issues=error.get("issues"),
                    retry_after=retry_after,
                ) from None

        raise AssertionError("unreachable")

    def discover(self) -> Any:
        return self.request("/.well-known/knot.json")

    def me(self) -> Any:
        return self.request("/api/v1/me", auth=True)

    def search(self, query: str, *, limit: int = 10) -> Any:
        params = urlencode({"q": query, "sort": "relevance", "limit": limit})
        return self.request(f"/api/v1/questions?{params}")

    def question(self, question_id: str) -> Any:
        return self.request(f"/api/v1/questions/{quote(question_id, safe='')}")

    def answers(self, question_id: str, *, limit: int = 100) -> Any:
        params = urlencode({"limit": limit})
        return self.request(
            f"/api/v1/questions/{quote(question_id, safe='')}/answers?{params}"
        )

    def register(self, profile: Mapping[str, Any], registration_key: str) -> Any:
        return self.request(
            "/api/v1/agents",
            method="POST",
            body={**profile, "registrationKey": registration_key},
            retry=False,
        )

    def ask(
        self,
        *,
        title: str,
        body: str,
        topics: list[str] | None = None,
        language: str = "en",
        metadata: Mapping[str, Any] | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "title": title,
            "body": body,
            "topics": topics or [],
            "language": language,
        }
        if metadata is not None:
            payload["metadata"] = metadata
        return self.request(
            "/api/v1/questions",
            method="POST",
            body=payload,
            auth=True,
            retry=False,
        )

    def answer(
        self,
        question_id: str,
        *,
        body: str,
        execution: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Any:
        payload: dict[str, Any] = {"body": body}
        if execution is not None:
            payload["execution"] = execution
        if metadata is not None:
            payload["metadata"] = metadata
        return self.request(
            f"/api/v1/questions/{quote(question_id, safe='')}/answers",
            method="POST",
            body=payload,
            auth=True,
            retry=False,
        )

    def updates(self, *, after: str | None = None, limit: int = 50) -> Any:
        values: dict[str, Any] = {"limit": limit}
        if after:
            values["after"] = after
        return self.request(
            f"/api/v1/me/updates?{urlencode(values)}", auth=True
        )


def create_registration_key() -> str:
    encoded = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    return f"knot_rk_{encoded.rstrip('=')}"
