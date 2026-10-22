from __future__ import annotations

from email.message import Message
import io
import json
import unittest
from urllib.error import HTTPError

from knot_agent_kit import KnotApiError, KnotClient, create_registration_key


class Response:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


class ClientTests(unittest.TestCase):
    def test_search_encodes_query_and_limit(self):
        seen = []

        def opener(request, **_kwargs):
            seen.append(request)
            return Response({"data": {"questions": []}})

        result = KnotClient(opener=opener).search("passkey recovery", limit=5)

        self.assertEqual(result["data"]["questions"], [])
        self.assertIn("q=passkey+recovery", seen[0].full_url)
        self.assertIn("limit=5", seen[0].full_url)
        self.assertEqual(
            seen[0].headers["User-agent"], "knot-agent-kit-python/0.1.0"
        )

    def test_authenticated_write_is_not_retried(self):
        calls = 0

        def opener(request, **_kwargs):
            nonlocal calls
            calls += 1
            headers = Message()
            headers["Retry-After"] = "1"
            raise HTTPError(
                request.full_url,
                429,
                "rate limited",
                headers,
                io.BytesIO(
                    b'{"error":{"code":"rate_limited","message":"Slow down"}}'
                ),
            )

        client = KnotClient(token="secret", opener=opener, sleep=lambda _s: None)
        with self.assertRaises(KnotApiError) as raised:
            client.ask(title="Question", body="Body")

        self.assertEqual(calls, 1)
        self.assertEqual(raised.exception.status, 429)

    def test_rate_limited_read_retries(self):
        calls = 0
        sleeps = []

        def opener(request, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                headers = Message()
                headers["Retry-After"] = "2"
                raise HTTPError(
                    request.full_url,
                    429,
                    "rate limited",
                    headers,
                    io.BytesIO(
                        b'{"error":{"code":"rate_limited","message":"Slow down"}}'
                    ),
                )
            return Response({"data": {"questions": []}})

        result = KnotClient(opener=opener, sleep=sleeps.append).search("retry")

        self.assertEqual(result["data"]["questions"], [])
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [2])

    def test_authenticated_method_requires_token_before_request(self):
        called = False

        def opener(_request, **_kwargs):
            nonlocal called
            called = True
            return Response({})

        with self.assertRaises(KnotApiError) as raised:
            KnotClient(opener=opener).me()

        self.assertFalse(called)
        self.assertEqual(raised.exception.code, "missing_token")

    def test_registration_key_shape(self):
        key = create_registration_key()
        self.assertTrue(key.startswith("knot_rk_"))
        self.assertNotIn("=", key)
        self.assertGreaterEqual(len(key), 51)


if __name__ == "__main__":
    unittest.main()
