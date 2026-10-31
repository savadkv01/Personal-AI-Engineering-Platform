"""Memory service (M5): CRUD, scope-filtered recall, sessions, consolidation, forgetting."""
from .config import MemoryConfig, load_memory_config
from .models import MemoryItem, Recalled, Session, Turn
from .service import MemoryService, open_service

__all__ = ["MemoryConfig", "MemoryItem", "MemoryService", "Recalled", "Session", "Turn",
           "load_memory_config", "open_service"]
