import json
import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.modules.identity.transport import AuthEndpoint


@pytest.fixture
def endpoint():
    return AuthEndpoint("http://127.0.0.1:19999", "http://127.0.0.1:19999", "test")


@pytest.fixture
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def public_key(signing_key):
    public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(signing_key.public_key()))
    return {**public, "kid": "test-key", "alg": "ES256", "use": "sig"}


@pytest.fixture
def claims(endpoint):
    now = int(time.time())
    return {
        "sub": str(uuid4()),
        "session_id": str(uuid4()),
        "aud": "authenticated",
        "iss": endpoint.issuer,
        "role": "authenticated",
        "iat": now,
        "exp": now + 900,
    }


@pytest.fixture
def encode(signing_key, claims):
    def token(overrides=None, *, key=None, kid="test-key", headers=None):
        return jwt.encode(
            {**claims, **(overrides or {})},
            key or signing_key,
            algorithm="ES256",
            headers={"kid": kid, **(headers or {})},
        )

    return token
