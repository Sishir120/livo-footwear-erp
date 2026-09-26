import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing_and_verification():
    password = "LivoERPSecretPass#2026"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_creation_and_decoding():
    payload = {"user_id": 42, "company_id": 1, "role": "editor"}
    token = create_access_token(payload)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["user_id"] == 42
    assert decoded["company_id"] == 1
    assert decoded["role"] == "editor"

def test_invalid_jwt_token():
    assert decode_access_token("invalid.jwt.token") is None
