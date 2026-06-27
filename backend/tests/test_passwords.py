from app.auth.passwords import hash_password, verify_password

def test_password_roundtrip():
    hashed = hash_password("password123")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("password123", hashed)
    assert not verify_password("wrong", hashed)
