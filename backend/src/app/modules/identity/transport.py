import json
from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Literal
from urllib.parse import urlsplit

import httpx

from app.modules.identity.contracts import (
    AuthenticationRejected,
    ProviderThrottled,
    ProviderUnavailable,
)

MAX_RESPONSE_BYTES = 65536


@dataclass(frozen=True)
class AuthEndpoint:
    """Deployment configuration only; never construct this from a token or request."""

    url: str
    issuer: str
    environment: Literal["local", "test", "staging", "production"]

    def __post_init__(self) -> None:
        for value in (self.url, self.issuer):
            try:
                parsed = urlsplit(value)
                port = parsed.port
            except ValueError:
                raise ValueError("Invalid authentication endpoint configuration") from None
            local_http = (
                self.environment in {"local", "test"}
                and parsed.scheme == "http"
                and parsed.hostname in {"127.0.0.1", "localhost", "auth"}
            )
            if (
                not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or port == 0
                or (parsed.scheme != "https" and not local_http)
                or value.endswith("/")
            ):
                raise ValueError("Invalid authentication endpoint configuration")


class AuthTransport:
    def __init__(self, endpoint: AuthEndpoint, *, transport: httpx.BaseTransport | None = None):
        self.endpoint = endpoint
        self._client = httpx.Client(
            timeout=httpx.Timeout(connect=2, read=3, write=3, pool=1),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        bearer: str | None = None,
        empty: bool = False,
    ) -> dict[str, object]:
        # Only internal constant paths reach here. No redirects, proxy inheritance,
        # retries, response-body logging or provider exceptions cross this boundary.
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        deadline = monotonic() + 8
        try:
            with self._client.stream(
                method,
                self.endpoint.url + path,
                json=payload,
                params=params,
                headers=headers,
            ) as response:
                if response.status_code == 429:
                    raise ProviderThrottled()
                if response.status_code >= 500:
                    raise ProviderUnavailable()
                if 400 <= response.status_code < 500:
                    raise AuthenticationRejected()
                if response.status_code not in ({204} if empty else {200}):
                    raise ProviderUnavailable()
                if empty:
                    return {}
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES or monotonic() > deadline:
                        raise ProviderUnavailable()
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise ProviderUnavailable()
                return result
        except (httpx.HTTPError, ValueError):
            raise ProviderUnavailable() from None
