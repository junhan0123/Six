"""server_globals — Server Global State (S79.7 compat stub)
Minimal compatibility layer for server globals.
"""

# Provider probe cache
_PROVIDER_PROBE_CACHE = {}

# Local peer flag
_is_local_peer = True

# SSE utilities (stub)
_sse_put = None
_sse_use_eventbus = False

# Proactive DnD state
_proactive_dnd_state = {}

# Remote allowed tools
_remote_allowed_tools = []

# Hotspot modal payload
_hotspot_modal_payload = {}

# CORS origins
_resolve_cors_origins = lambda: ["*"]
_CORS_ALLOWED_ORIGINS = ["*"]
_ACCESS_LOG_REDACT_RE = None
_REMOTE_FORBIDDEN = False

# Briefing lock
BRIEFING_LOCK = None
