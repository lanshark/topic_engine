# sources/fetching/strategies/__init__.py
from .archive import ArchiveStrategy
from .browser import BrowserStrategy
from .simple import SimpleHttpStrategy

__all__ = [
    "SimpleHttpStrategy",
    "BrowserStrategy",
    "ArchiveStrategy",
]
