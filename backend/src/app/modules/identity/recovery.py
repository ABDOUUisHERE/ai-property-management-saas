"""Single-use provider recovery and a durable local session barrier."""

import secrets
from datetime import timedelta
from typing import Protocol
from uuid import uuid4

from pydantic import SecretStr

from app.core.context import Clock
from app.modules.identity.contracts import (
    AuthenticatedAccount,
    AuthenticationRejected,
    ProviderThrottled,
    ProviderUnavailable,
)
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.sessions import SessionBusy

# Supabase renders this public configuration asset, never a user's input.
# A fragment is not sent in HTTP requests, proxy access logs or Referer headers.
RECOVERY_TEMPLATE = """<!doctype html><html lang="fr"><meta charset="utf-8">
<h1>Réinitialiser votre mot de passe</h1>
<p><a href="{{ .SiteURL }}/auth/reset#token_hash={{ .TokenHash }}">
Choisir un nouveau mot de passe</a></p>
<p>Ce lien expire après une heure et ne peut servir qu'une fois.
Si vous n'avez pas demandé ce changement, ignorez cet email.</p></html>"""


class RecoveryAuthority(Protocol):
    def request_recovery(self, email: str, *, redirect_to: str) -> None: ...
    def verify_recovery(self, token_hash: SecretStr) -> AuthenticatedAccount: ...
    def change_recovered_password(
        self, account: AuthenticatedAccount, password: SecretStr
    ) -> None: ...
    def logout(self, access_token: SecretStr) -> None: ...


class RecoveryService:
    def __init__(
        self,
        repository: IdentityRepository,
        authority: RecoveryAuthority,
        clock: Clock,
        *,
        browser_origin: str,
    ):
        self._repository, self._authority, self._clock = repository, authority, clock
        # browser_origin has already passed BrowserSecurity's exact-origin validation.
        self._redirect = browser_origin + "/auth/reset"

    def request(self, email: str) -> None:
        try:
            self._authority.request_recovery(email, redirect_to=self._redirect)
        except (AuthenticationRejected, ProviderThrottled):
            pass  # Same public result for known, unknown and upstream-limited accounts.

    def confirm(self, token_hash: SecretStr, password: SecretStr) -> None:
        account = self._authority.verify_recovery(token_hash)
        owner, capability = uuid4(), secrets.token_hex(32)
        try:
            with self._repository.transaction(
                session_hash=capability, verified_subject=account.identity.subject
            ) as transaction:
                now = self._clock.now()
                transaction.upsert_profile(account.identity.subject, account.email, now)
                if not transaction.begin_recovery(
                    account.identity.subject, owner, now, now + timedelta(seconds=30)
                ):
                    raise SessionBusy()
            # Committed barrier precedes the network. An ambiguous failure leaves
            # it closed; a new recovery email can restart after the lease expires.
            self._authority.change_recovered_password(account, password)
            with self._repository.transaction(
                session_hash=capability, verified_subject=account.identity.subject
            ) as transaction:
                if not transaction.finish_recovery(
                    account.identity.subject, owner, self._clock.now()
                ):
                    raise SessionBusy()
        finally:
            try:
                self._authority.logout(account.tokens.access_token)
            except (AuthenticationRejected, ProviderUnavailable):
                pass
