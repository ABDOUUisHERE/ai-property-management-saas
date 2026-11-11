import base64
import binascii
import json
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.modules.identity.contracts import ProviderTokens


class InvalidTokenEnvelope(Exception):
    def __init__(self) -> None:
        super().__init__("Stored session tokens cannot be decrypted")


@dataclass(frozen=True)
class SessionBinding:
    session_hash: str
    subject: UUID

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", self.session_hash) or not self.subject.int:
            raise ValueError("Invalid session binding")

    def associated_data(self, key_id: str) -> bytes:
        return f"pms.auth.v1:{key_id}:{self.session_hash}:{self.subject}".encode("ascii")


class TokenVault:
    """AEAD envelope bound to its session row; the keyring lives outside the DB.

    Keep old keys during rotation, write with the active key, then re-encrypt
    retained rows before removing an old key. Session expiry is enforced by the
    session service, not by this encryption primitive.
    """

    def __init__(self, keys: Mapping[str, SecretStr], *, active_key_id: str):
        self._keys: dict[str, AESGCM] = {}
        if not 1 <= len(keys) <= 8 or active_key_id not in keys:
            raise ValueError("Invalid session encryption keyring")
        try:
            for key_id, encoded in keys.items():
                if not re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", key_id):
                    raise ValueError
                key = base64.b64decode(encoded.get_secret_value(), altchars=b"-_", validate=True)
                if len(key) != 32:
                    raise ValueError
                self._keys[key_id] = AESGCM(key)
        except (ValueError, binascii.Error):
            raise ValueError("Invalid session encryption keyring") from None
        self._active = active_key_id

    def encrypt(self, tokens: ProviderTokens, binding: SessionBinding) -> str:
        values = [tokens.access_token.get_secret_value(), tokens.refresh_token.get_secret_value()]
        if not 1 <= len(values[0]) <= 16384 or not 1 <= len(values[1]) <= 4096:
            raise InvalidTokenEnvelope()
        body = json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        if len(body) > 32768:
            raise InvalidTokenEnvelope()
        nonce = secrets.token_bytes(12)
        cipher = self._keys[self._active].encrypt(
            nonce, body, binding.associated_data(self._active)
        )
        return f"v1.{self._active}." + base64.urlsafe_b64encode(nonce + cipher).decode("ascii")

    def decrypt(self, envelope: str, binding: SessionBinding) -> ProviderTokens:
        if not 1 <= len(envelope) <= 65536:
            raise InvalidTokenEnvelope()
        try:
            version, key_id, encoded = envelope.split(".")
            if version != "v1" or key_id not in self._keys:
                raise InvalidTokenEnvelope()
            packed = base64.b64decode(encoded, altchars=b"-_", validate=True)
            if len(packed) < 28:
                raise InvalidTokenEnvelope()
            plain = self._keys[key_id].decrypt(
                packed[:12], packed[12:], binding.associated_data(key_id)
            )
            values = json.loads(plain)
            if (
                not isinstance(values, list)
                or len(values) != 2
                or not all(isinstance(value, str) for value in values)
                or not 1 <= len(values[0]) <= 16384
                or not 1 <= len(values[1]) <= 4096
            ):
                raise InvalidTokenEnvelope()
            return ProviderTokens(SecretStr(values[0]), SecretStr(values[1]))
        except (ValueError, binascii.Error, InvalidTag):
            raise InvalidTokenEnvelope() from None
