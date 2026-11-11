"""Recovery requests do not query local profiles or expose provider account state."""

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.context import SystemClock
from app.modules.identity.contracts import (
    AuthenticationRejected,
    ProviderThrottled,
    ProviderUnavailable,
)
from app.modules.identity.recovery import RecoveryService
from app.modules.identity.repository import IdentityRepository


class Authority:
    def __init__(self, failure):
        self.failure, self.calls = failure, []

    def request_recovery(self, email, *, redirect_to):
        self.calls.append((email, redirect_to))
        if self.failure:
            raise self.failure()


@pytest.mark.parametrize("failure", [None, AuthenticationRejected, ProviderThrottled])
def test_request_hides_account_rejection_and_throttling_without_a_database(failure):
    authority = Authority(failure)
    service = RecoveryService(
        IdentityRepository(sessionmaker()),
        authority,
        SystemClock(),
        browser_origin="https://property.example.test",
    )
    assert service.request("fiction@example.test") is None
    assert authority.calls == [("fiction@example.test", "https://property.example.test/auth/reset")]


def test_request_reports_provider_outage_without_retries_or_a_database():
    authority = Authority(ProviderUnavailable)
    service = RecoveryService(
        IdentityRepository(sessionmaker()),
        authority,
        SystemClock(),
        browser_origin="https://property.example.test",
    )
    with pytest.raises(ProviderUnavailable):
        service.request("fiction@example.test")
    assert len(authority.calls) == 1
