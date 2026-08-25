"""Shared TLS trust configuration for backend external clients."""

from __future__ import annotations

import os
from pathlib import Path


_CA_BUNDLE_ENV_VARS = ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE")


def tls_verify_setting() -> str | bool:
    """Return the verified system trust store or an explicit CA bundle."""
    for variable in _CA_BUNDLE_ENV_VARS:
        candidate = os.environ.get(variable)
        if candidate:
            if not Path(candidate).is_file():
                raise ValueError(f"configured CA bundle does not exist: {candidate}")
            return candidate
    return True