import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.modules.identity.contracts import AuthenticationRejected, ProviderUnavailable
from app.modules.identity.transport import AuthTransport
from app.modules.identity.verification import AccessTokenVerifier


def verifier(endpoint, keys, *, monotonic=lambda: 0):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"keys": keys})

    transport = AuthTransport(endpoint, transport=httpx.MockTransport(handler))
    return transport, AccessTokenVerifier(transport, monotonic=monotonic), requests


def test_verified_subject_is_typed_and_concurrent_cache_is_shared(
    endpoint, public_key, encode, claims
):
    transport, check, requests = verifier(endpoint, [public_key])
    try:
        token = encode()
        with ThreadPoolExecutor(max_workers=12) as pool:
            identities = list(pool.map(check.verify, [token] * 24))
        assert all(identity.subject == UUID(claims["sub"]) for identity in identities)
        assert identities[0].provider_session_id == UUID(claims["session_id"])
        assert len(requests) == 1
        assert requests[0].url.path == "/.well-known/jwks.json"
        assert "authorization" not in requests[0].headers
    finally:
        transport.close()


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://foreign.example.test"},
        {"aud": "service_role"},
        {"aud": ["authenticated"]},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"sub": "not-a-uuid"},
        {"sub": str(UUID(int=0))},
        {"session_id": None},
        {"session_id": str(UUID(int=0))},
        {"iat": 1, "exp": 2},
        {"iat": True},
        {"exp": "9999999999"},
        {"nbf": 9999999999},
        {"iat": 9999999998, "exp": 9999999999},
    ],
)
def test_invalid_claims_are_rejected(endpoint, public_key, encode, overrides):
    transport, check, _ = verifier(endpoint, [public_key])
    try:
        with pytest.raises(AuthenticationRejected):
            check.verify(encode(overrides))
    finally:
        transport.close()


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "aud", "sub", "session_id", "role"])
def test_required_claim_cannot_be_omitted(endpoint, public_key, signing_key, claims, missing):
    claims.pop(missing)
    token = jwt.encode(claims, signing_key, algorithm="ES256", headers={"kid": "test-key"})
    transport, check, _ = verifier(endpoint, [public_key])
    try:
        with pytest.raises(AuthenticationRejected):
            check.verify(token)
    finally:
        transport.close()


def test_forged_signature_algorithm_and_untrusted_key_url(endpoint, public_key, encode, claims):
    transport, check, requests = verifier(endpoint, [public_key])
    try:
        foreign = ec.generate_private_key(ec.SECP256R1())
        for token in (
            encode(key=foreign),
            encode(headers={"crit": ["foreign"]}),
            jwt.encode(claims, "x" * 48, algorithm="HS256", headers={"kid": "test-key"}),
            jwt.encode(claims, "", algorithm="none"),
            "bad",
            "x" * 16385,
        ):
            with pytest.raises(AuthenticationRejected):
                check.verify(token)
        # Header URLs never select a key source. Only the configured endpoint is contacted.
        assert check.verify(encode(headers={"jku": "https://attacker.example.test/keys"}))
        assert all(request.url.host == "127.0.0.1" for request in requests)
    finally:
        transport.close()


def test_rotation_revocation_and_unknown_kid_requests_are_bounded(endpoint, public_key, encode):
    instant = [0]
    keys = [public_key]
    transport, check, requests = verifier(endpoint, keys, monotonic=lambda: instant[0])
    try:
        check.verify(encode())
        new_private = ec.generate_private_key(ec.SECP256R1())
        new_public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(new_private.public_key()))
        keys.append({**new_public, "kid": "rotated", "alg": "ES256"})
        check.verify(encode(key=new_private, kid="rotated"))
        assert len(requests) == 2
        for index in range(30):
            with pytest.raises(AuthenticationRejected):
                check.verify(encode(kid=f"unknown-{index}"))
        assert len(requests) == 2
        keys.pop(0)
        instant[0] = 61
        with pytest.raises(AuthenticationRejected):
            check.verify(encode())
        check.verify(encode(key=new_private, kid="rotated"))
        assert len(requests) == 3
    finally:
        transport.close()


@pytest.mark.parametrize("mutation", ["private", "symmetric", "duplicate", "wrong-curve", "empty"])
def test_invalid_key_sets_fail_closed(endpoint, public_key, encode, mutation):
    keys = [public_key]
    if mutation == "private":
        public_key["d"] = "private-material"
    elif mutation == "symmetric":
        public_key["kty"] = "oct"
    elif mutation == "wrong-curve":
        public_key["crv"] = "P-384"
    elif mutation == "duplicate":
        keys.append(public_key)
    else:
        keys.clear()
    transport, check, _ = verifier(endpoint, keys)
    try:
        with pytest.raises(ProviderUnavailable):
            check.verify(encode())
    finally:
        transport.close()


def test_expired_cache_does_not_use_stale_keys_on_provider_outage(endpoint, public_key, encode):
    instant = [0]

    def handler(request):
        return (
            httpx.Response(200, json={"keys": [public_key]})
            if instant[0] == 0
            else httpx.Response(503, text="sensitive-provider-detail")
        )

    transport = AuthTransport(endpoint, transport=httpx.MockTransport(handler))
    try:
        check = AccessTokenVerifier(transport, monotonic=lambda: instant[0])
        check.verify(encode())
        instant[0] = 61
        with pytest.raises(ProviderUnavailable) as error:
            check.verify(encode())
        assert "sensitive" not in str(error.value)
    finally:
        transport.close()


def test_lifetime_and_numeric_dates_are_strict(endpoint, public_key, encode, claims):
    transport, check, _ = verifier(endpoint, [public_key])
    try:
        for overrides in (
            {"exp": claims["iat"] + 3601},
            {"iat": float(claims["iat"])},
            {"exp": float(claims["exp"])},
            {"exp": claims["iat"] - 10},
        ):
            with pytest.raises(AuthenticationRejected):
                check.verify(encode(overrides))
    finally:
        transport.close()
