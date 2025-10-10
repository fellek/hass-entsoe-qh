# Changelog

## [0.4.6] - 2025-10-11
### Fixed
- Removed the duplicate setup warning so the integration can be added without the `already_configured` message.

## [0.4.5] - 2025-10-11
### Fixed
- Allow timezone-sensitive tests to fall back to a fixed offset when the system tzdata package is unavailable, ensuring Windows compatibility.

## [0.4.4] - 2025-10-10
### Fixed
- Align price series generation with the ENTSO-E bidding zone timezone to ensure sensors expose full price data right after integration setup.
- Add regression coverage for timezone-sensitive series generation.
