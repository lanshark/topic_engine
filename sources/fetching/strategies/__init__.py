# sources/fetching/strategies/__init__.py
from .simple import SimpleHttpStrategy
from .browser import BrowserStrategy
from .archive import ArchiveStrategy

__all__ = [
    'SimpleHttpStrategy',
    'BrowserStrategy',
    'ArchiveStrategy',
]