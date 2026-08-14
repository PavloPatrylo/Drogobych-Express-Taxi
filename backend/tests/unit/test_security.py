"""
Unit tests for core security utilities (hash_password, verify_password).
"""
import pytest
from app.core.security import hash_password, verify_password


def test_hash_password_and_verify_success():
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True


def test_verify_password_failure():
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)

    assert verify_password("WrongPassword!", hashed) is False


def test_password_truncation_handling():
    # Passwords longer than 72 bytes should be safely truncated without crashing bcrypt
    long_password = "A" * 100
    hashed = hash_password(long_password)

    assert verify_password(long_password, hashed) is True
    # Password matching first 72 bytes should verify due to bcrypt limit
    assert verify_password("A" * 72, hashed) is True
    assert verify_password("A" * 71, hashed) is False
