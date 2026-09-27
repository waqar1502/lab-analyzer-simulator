from __future__ import annotations


def calculate_checksum(content: bytes) -> str:
    """Return the ASTM two-character uppercase modulo-256 checksum."""
    return f"{sum(content) % 256:02X}"
