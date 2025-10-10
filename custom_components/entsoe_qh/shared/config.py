from __future__ import annotations

from .constants import DEFAULT_DOMAIN


def generate_unique_id(domain: str | None) -> str:
    effective_domain = (domain or DEFAULT_DOMAIN).strip()
    return f"{effective_domain}_{effective_domain}"
