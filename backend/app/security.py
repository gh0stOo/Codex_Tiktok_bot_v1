from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
import base64
import os


def get_fernet(secret: str) -> Fernet:
    key = secret
    if len(secret) != 44:
        key = base64.urlsafe_b64encode(secret.encode().ljust(32, b"0"))
    return Fernet(key)


def encrypt_secret(secret: str, fernet_key: str) -> str:
    f = get_fernet(fernet_key)
    return f.encrypt(secret.encode()).decode()


def decrypt_secret(token: str, fernet_key: str) -> Optional[str]:
    f = get_fernet(fernet_key)
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        return None
