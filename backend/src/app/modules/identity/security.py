"""Browser transport policy and atomic, privacy-preserving rate limits."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Protocol
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response
from redis import Redis
from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import Clock
from app.core.errors import ApplicationError, problem_response


class RateLimit(Protocol):
    def check(self, bucket: str, subject: str, limit: int, window: int) -> None: ...


class RedisRateLimit:
    def __init__(self, client: Redis[bytes], key: bytes):
        self._client, self._key = client, key

    def check(self, bucket: str, subject: str, limit: int, window: int) -> None:
        digest = hmac.new(
            self._key, f"pms.rate:{bucket}:{subject}".encode(), hashlib.sha256
        ).hexdigest()
        try:
            count = self._client.execute_command(
                "EVAL",
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
                1,
                f"pms:rate:{digest}",
                window,
            )
        except RedisError:
            raise ApplicationError(503, "auth_unavailable", "Service unavailable") from None
        if not isinstance(count, int):
            raise ApplicationError(503, "auth_unavailable", "Service unavailable")
        if count > limit:
            raise ApplicationError(429, "rate_limited", "Too many requests", retry_after=window)


class BrowserSecurity:
    def __init__(self, origin: str, environment: str, secret: bytes, clock: Clock):
        parsed = urlsplit(origin)
        local = (
            environment in {"local", "test"}
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
        )
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path
            or (parsed.scheme != "https" and not local)
            or len(secret) < 48
        ):
            raise ValueError("An exact HTTPS browser origin and a CSRF secret are required")
        self.origin, self.secure = origin, parsed.scheme == "https"
        prefix = "__Host-" if self.secure else ""
        self.session_cookie, self.context_cookie = (
            prefix + "pms_session",
            prefix + "pms_csrf_context",
        )
        self._secret, self._clock = secret, clock

    def cookie(self, response: Response, name: str, value: str, max_age: int) -> None:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            path="/",
            secure=self.secure,
            httponly=True,
            samesite="lax",
        )

    def clear(self, response: Response, name: str) -> None:
        response.delete_cookie(name, path="/", secure=self.secure, httponly=True, samesite="lax")

    def issue(self, request: Request, response: Response) -> str:
        binding = self._binding(request)
        if binding is None:
            binding = secrets.token_urlsafe(32)
            self.cookie(response, self.context_cookie, binding, 3600)
        issued, nonce = str(int(self._clock.now().timestamp())), secrets.token_urlsafe(32)
        return f"v1.{issued}.{nonce}.{self._signature(binding, issued, nonce)}"

    def validate(self, request: Request) -> None:
        if (
            request.headers.get("origin") != self.origin
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            raise ApplicationError(403, "origin_rejected", "Request rejected")
        binding, token = self._binding(request), request.headers.get("x-csrf-token", "")
        try:
            if binding is None or len(token) > 256:
                raise ValueError
            version, issued, nonce, signature = token.split(".")
            age = int(self._clock.now().timestamp()) - int(issued)
            if (
                version != "v1"
                or not re.fullmatch(r"[a-zA-Z0-9_-]{43}", nonce)
                or not -5 <= age <= 3600
                or not hmac.compare_digest(signature, self._signature(binding, issued, nonce))
            ):
                raise ValueError
        except (ValueError, TypeError):
            raise ApplicationError(403, "csrf_rejected", "Request rejected") from None

    def _binding(self, request: Request) -> str | None:
        for name in (self.session_cookie, self.context_cookie):
            value = request.cookies.get(name)
            if value and re.fullmatch(r"[a-zA-Z0-9_-]{43}", value):
                return value
        return None

    def _signature(self, binding: str, issued: str, nonce: str) -> str:
        binding_hash = hashlib.sha256(binding.encode("ascii")).hexdigest()
        return hmac.new(
            self._secret, f"pms.csrf.v1:{binding_hash}:{issued}:{nonce}".encode(), hashlib.sha256
        ).hexdigest()


class AuthGuard:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        auth_path = request.url.path.startswith("/api/v1/auth/") or request.url.path == "/api/v1/me"
        private_json_path = (
            auth_path
            or request.url.path == "/api/v1/organizations"
            or request.url.path.startswith("/api/v1/organizations/")
        )
        received = 0

        async def bounded_receive() -> Message:
            nonlocal received
            message = await receive()
            if private_json_path and message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > 8192:
                    raise HTTPException(413)
            return message

        async def safe_send(message: Message) -> None:
            if private_json_path and message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                message = {
                    **message,
                    "headers": headers
                    + [(b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff")],
                }
            await send(message)

        try:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                request.app.state.auth_security.validate(request)
                if auth_path:
                    await run_in_threadpool(
                        request.app.state.auth_limiter.check,
                        "auth-ip",
                        request.client.host if request.client else "unknown",
                        30,
                        60,
                    )
            elif request.url.path == "/api/v1/auth/csrf":
                if request.headers.get("origin") not in {
                    None,
                    request.app.state.auth_security.origin,
                }:
                    raise ApplicationError(403, "origin_rejected", "Request rejected")
                await run_in_threadpool(
                    request.app.state.auth_limiter.check,
                    "csrf-ip",
                    request.client.host if request.client else "unknown",
                    60,
                    60,
                )
        except ApplicationError as error:
            response = problem_response(request, error.status, error.code, error.title)
            if error.status == 429:
                response.headers["Retry-After"] = str(error.retry_after or 60)
            await response(scope, receive, safe_send)
            return
        await self.app(scope, bounded_receive, safe_send)
