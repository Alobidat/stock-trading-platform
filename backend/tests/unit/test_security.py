"""Tests for security utilities."""

import pytest
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    """Hashed password should verify correctly."""
    password = "SecureP@ssw0rd!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_wrong_password_fails():
    """Wrong password should not verify."""
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_jwt_create_and_decode():
    """Token created for a subject should decode to the same subject."""
    subject = "user-123"
    token = create_access_token(subject)
    decoded = decode_access_token(token)
    assert decoded == subject


def test_invalid_token_returns_none():
    """Garbage token should return None."""
    result = decode_access_token("not.a.valid.token")
    assert result is None


def test_tampered_token_returns_none():
    """Tampered token should return None."""
    token = create_access_token("user-456")
    tampered = token[:-5] + "XXXXX"
    result = decode_access_token(tampered)
    assert result is None
