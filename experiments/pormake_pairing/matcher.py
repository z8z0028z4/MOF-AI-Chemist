"""Compatibility import for the production PORMAKE pairing engine."""

from backend.services.mof.pormake_pairing import (
    PairingCandidate,
    PairingMatcher,
    PairingResult,
    PormakeFragmentIndex,
)

__all__ = [
    "PairingCandidate",
    "PairingMatcher",
    "PairingResult",
    "PormakeFragmentIndex",
]
