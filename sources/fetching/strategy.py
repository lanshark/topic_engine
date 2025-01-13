# sources/fetching/strategy.py
from enum import Enum, auto


class FetchStrategy(Enum):
    """Available fetch strategies"""

    SIMPLE = auto()  # Direct HTTP request
    BROWSER = auto()  # Browser simulation
    ARCHIVE = auto()  # Archive services

    def __str__(self):
        return self.name.lower()
