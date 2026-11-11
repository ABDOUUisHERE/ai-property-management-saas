import math
import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID

import jwt

from app.modules.identity.contracts import (
    AuthenticationRejected,
    ProviderUnavailable,
    VerifiedIdentity,
)
from app.modules.identity.transport import AuthTransport


class AccessTokenVerifier:
    """Only configured ES256 public keys can authenticate a Supabase subject."""

    def __init__(
        self, transport: AuthTransport, *, monotonic: Callable[[], float] = time.monotonic
    ):
        self._transport = transport
        self._monotonic = monotonic
        self._keys: dict[str, jwt.PyJWK] = {}
        self._expires = -math.inf
        self._last_miss_refresh = -math.inf
        self._lock = Lock()

    def verify(self, token: str) -> VerifiedIdentity:
        if not 1 <= len(token) <= 16384:
            raise AuthenticationRejected()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if (
                header.get("alg") != "ES256"
                or not isinstance(kid, str)
                or not 1 <= len(kid) <= 128
                or "crit" in header
            ):
                raise AuthenticationRejected()
            key = self._key(kid)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["ES256"],
                issuer=self._transport.endpoint.issuer,
                audience="authenticated",
                leeway=5,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "session_id", "role"],
                    "strict_aud": True,
                },
            )
            issued, expires = claims["iat"], claims["exp"]
            if (
                type(issued) is not int
                or type(expires) is not int
                or not 0 < expires - issued <= 3600
                or claims["role"] != "authenticated"
                or claims.get("is_anonymous", False) is not False
            ):
                raise AuthenticationRejected()
            subject, session = UUID(claims["sub"]), UUID(claims["session_id"])
            if not subject.int or not session.int:
                raise AuthenticationRejected()
            return VerifiedIdentity(
                subject,
                session,
                datetime.fromtimestamp(issued, UTC),
                datetime.fromtimestamp(expires, UTC),
            )
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError, OverflowError):
            raise AuthenticationRejected() from None

    def _key(self, kid: str) -> jwt.PyJWK:
        # One bounded cache per adapter. Unknown attacker-controlled kids cannot
        # allocate entries or force more than one extra JWKS request per 10 seconds.
        with self._lock:
            now = self._monotonic()
            fetched = False
            if now >= self._expires:
                self._load_keys()
                self._expires = now + 60
                fetched = True
            if kid not in self._keys and not fetched and now - self._last_miss_refresh >= 10:
                self._last_miss_refresh = now
                self._load_keys()
                self._expires = now + 60
            if kid not in self._keys:
                raise AuthenticationRejected()
            return self._keys[kid]

    def _load_keys(self) -> None:
        payload = self._transport.request("GET", "/.well-known/jwks.json")
        candidates = payload.get("keys")
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= 16:
            raise ProviderUnavailable()
        keys: dict[str, jwt.PyJWK] = {}
        try:
            for item in candidates:
                if (
                    not isinstance(item, dict)
                    or item.get("kty") != "EC"
                    or item.get("crv") != "P-256"
                    or item.get("alg", "ES256") != "ES256"
                    or item.get("use", "sig") != "sig"
                    or item.get("key_ops", ["verify"]) != ["verify"]
                    or any(private in item for private in ("d", "k", "p", "q"))
                ):
                    raise ProviderUnavailable()
                kid = item.get("kid")
                if not isinstance(kid, str) or not 1 <= len(kid) <= 128 or kid in keys:
                    raise ProviderUnavailable()
                keys[kid] = jwt.PyJWK.from_dict(item, algorithm="ES256")
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise ProviderUnavailable() from None
        # Replace the whole set so revoked keys disappear at the next refresh.
        self._keys = keys
