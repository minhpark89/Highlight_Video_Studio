"""Local credential storage boundary for the connector.

Production Windows packaging must supply a DPAPI-backed implementation. The
Phase 1 skeleton deliberately refuses plaintext file persistence.
"""

import os
from typing import Protocol


class CredentialStore(Protocol):
    def load(self) -> str: ...
    def save(self, credential: str) -> None: ...


class EnvironmentCredentialStore:
    """Development/CI store; the secret is supplied by the process supervisor."""

    def __init__(self, variable: str = "HIGHLIGHT_DEVICE_CREDENTIAL"):
        self.variable = variable

    def load(self) -> str:
        value = os.environ.get(self.variable, "")
        if not value:
            raise RuntimeError(f"protected device credential is unavailable ({self.variable})")
        return value

    def save(self, credential: str) -> None:
        raise RuntimeError("plaintext credential persistence is disabled; use Windows DPAPI/credential manager")
