"""server_handlers — Server Handlers Module
Re-exports all handler mixins for backward compatibility.
"""

from server_handlers_system import SystemMixin
from server_handlers_memory import MemoryMixin
from server_handlers_chat import ChatMixin, CapabilityMixin
from server_handlers_system import TasksMixin, SocialMixin

__all__ = [
    'SystemMixin',
    'MemoryMixin',
    'TasksMixin',
    'ChatMixin',
    'CapabilityMixin',
    'SocialMixin',
]
