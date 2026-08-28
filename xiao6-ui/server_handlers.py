"""server_handlers — Server Handlers Module (S79.8)
Re-exports all handler mixins for backward compatibility.
"""

from server_handlers_chat import ChatMixin
from server_handlers_memory import MemoryMixin
from server_handlers_system import SystemMixin

# Check what else is available
try:
    from server_handlers_system import TasksMixin
except ImportError:
    class TasksMixin:
        pass

try:
    from server_handlers_system import SocialMixin
except ImportError:
    class SocialMixin:
        pass

# CapabilityMixin stub
class CapabilityMixin:
    """Stub capability mixin for server handlers."""
    pass

__all__ = [
    'SystemMixin',
    'MemoryMixin',
    'TasksMixin',
    'ChatMixin',
    'CapabilityMixin',
    'SocialMixin',
]
