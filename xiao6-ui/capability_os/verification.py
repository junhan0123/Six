"""capability_os.verification — Capability Verification (stub)
Stub module for capability verification.
"""

# Status constants
READY = "ready"
DECLARED = "declared"
PARTIAL = "partial"
BLOCKED = "blocked"
UNAVAILABLE = "unavailable"
ERROR = "error"


def verify_capability(cap_id: str) -> dict:
    """Verify a single capability. Returns stub result."""
    return {
        "id": cap_id,
        "status": READY,
        "error": None,
        "details": {}
    }


def verify_all() -> list:
    """Verify all capabilities. Returns empty list (stub)."""
    return []


def health_summary() -> dict:
    """Return health summary. Returns stub."""
    return {
        "total": 0,
        "ready": 0,
        "blocked": 0,
        "error": 0
    }
