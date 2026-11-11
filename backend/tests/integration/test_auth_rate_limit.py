import hashlib
import hmac
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import Settings
from app.core.errors import ApplicationError
from app.modules.identity.security import RedisRateLimit

pytestmark = pytest.mark.integration


def test_atomic_rate_limit_retains_expiry_and_stores_no_email():
    if os.environ.get("PMS_INTEGRATION") != "1":
        pytest.skip("Use scripts/application.py test for the isolated local Redis")
    settings = Settings()
    assert settings.redis_host == "127.0.0.1" and settings.environment in {"local", "test"}
    client = Redis.from_url(settings.broker_url(), socket_timeout=2, socket_connect_timeout=2)
    secret, email = secrets.token_bytes(32), f"limit-{uuid4().hex}@example.test"
    digest = hmac.new(secret, f"pms.rate:login-email:{email}".encode(), hashlib.sha256).hexdigest()
    owned_key = f"pms:rate:{digest}"
    limiter = RedisRateLimit(client, secret)

    def attempt(_):
        try:
            limiter.check("login-email", email, 5, 60)
            return True
        except ApplicationError as error:
            assert error.status == 429
            return False

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(20)))
        assert sum(results) == 5
        assert 0 < client.ttl(owned_key) <= 60
        assert email not in owned_key and b"@" not in client.get(owned_key)
    finally:
        client.delete(owned_key)  # Only this random test key, never FLUSHDB or a wildcard.
        client.close()


def test_limiter_connection_failure_is_sanitized():
    class FailedRedis:
        def execute_command(self, *args):
            raise RedisConnectionError("private-redis-password")

    with pytest.raises(ApplicationError) as error:
        RedisRateLimit(FailedRedis(), secrets.token_bytes(32)).check(
            "test", "fiction@example.test", 5, 60
        )
    assert error.value.status == 503
    assert "private" not in error.value.title
