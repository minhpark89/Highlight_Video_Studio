import hashlib
import hmac
import json
import re
import secrets
from typing import Any


SENSITIVE_KEY = re.compile(
    r"(^|_)(api_?key|token|secret|password|passwd|cookie|authorization|credential|private_?key)($|_)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?i)(bearer\s+[a-z0-9._~+/=-]+|(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+)"
)


def new_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def token_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str, iterations: int = 240_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, raw_iterations, raw_salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(raw_salt), int(raw_iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (TypeError, ValueError):
        return False


def find_sensitive_path(value: Any, path: str = "payload") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if SENSITIVE_KEY.search(str(key)):
                return child_path
            found = find_sensitive_path(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_sensitive_path(child, f"{path}[{index}]")
            if found:
                return found
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        return path
    return None


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact(child) for child in value]
    if isinstance(value, str):
        return SENSITIVE_VALUE.sub("[REDACTED]", value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
