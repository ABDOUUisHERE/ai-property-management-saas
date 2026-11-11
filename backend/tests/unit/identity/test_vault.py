import base64
import secrets
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.modules.identity.contracts import ProviderTokens
from app.modules.identity.vault import InvalidTokenEnvelope, SessionBinding, TokenVault


def key():
    return SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())


@pytest.fixture
def tokens():
    return ProviderTokens(SecretStr("private-access-token"), SecretStr("private-refresh-token"))


@pytest.fixture
def binding():
    return SessionBinding(secrets.token_hex(32), uuid4())


def test_randomized_authenticated_encryption_and_rotation(tokens, binding):
    old_key, new_key = key(), key()
    old = TokenVault({"old": old_key}, active_key_id="old")
    envelope = old.encrypt(tokens, binding)
    assert old.encrypt(tokens, binding) != envelope
    assert "private" not in envelope
    assert old.decrypt(envelope, binding) == tokens
    rotated = TokenVault({"old": old_key, "new": new_key}, active_key_id="new")
    assert rotated.decrypt(envelope, binding) == tokens
    rewritten = rotated.encrypt(rotated.decrypt(envelope, binding), binding)
    assert rewritten.startswith("v1.new.")
    retired = TokenVault({"new": new_key}, active_key_id="new")
    assert retired.decrypt(rewritten, binding) == tokens
    with pytest.raises(InvalidTokenEnvelope):
        retired.decrypt(envelope, binding)
    assert "private" not in repr(tokens)
    assert old_key.get_secret_value() not in repr(old)


@pytest.mark.parametrize("failure", ["subject", "session", "key", "tamper", "version", "truncated"])
def test_ciphertext_cannot_move_to_another_session_or_subject(tokens, binding, failure):
    vault = TokenVault({"key": key()}, active_key_id="key")
    envelope = vault.encrypt(tokens, binding)
    target = binding
    if failure == "subject":
        target = SessionBinding(binding.session_hash, uuid4())
    elif failure == "session":
        target = SessionBinding(secrets.token_hex(32), binding.subject)
    elif failure == "key":
        vault = TokenVault({"key": key()}, active_key_id="key")
    elif failure == "tamper":
        packed = bytearray(base64.urlsafe_b64decode(envelope.split(".")[2]))
        packed[-1] ^= 1
        envelope = "v1.key." + base64.urlsafe_b64encode(packed).decode()
    elif failure == "version":
        envelope = envelope.replace("v1.", "v2.", 1)
    else:
        envelope = "v1.key." + base64.urlsafe_b64encode(b"too-short").decode()
    with pytest.raises(InvalidTokenEnvelope) as error:
        vault.decrypt(envelope, target)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("envelope", ["", "x" * 65537, "v1.key.!!!!", "v1.key.eA==.extra"])
def test_invalid_envelopes_are_bounded(binding, envelope):
    vault = TokenVault({"key": key()}, active_key_id="key")
    with pytest.raises(InvalidTokenEnvelope):
        vault.decrypt(envelope, binding)


@pytest.mark.parametrize(
    "keys,active",
    [
        ({}, "key"),
        ({"key": "invalid"}, "key"),
        ({"bad.key": "a" * 44}, "bad.key"),
        ({"key": "a" * 44}, "absent"),
    ],
)
def test_invalid_key_configuration_is_sanitized(keys, active):
    with pytest.raises(ValueError) as error:
        TokenVault({name: SecretStr(value) for name, value in keys.items()}, active_key_id=active)
    assert "input_value" not in str(error.value)
