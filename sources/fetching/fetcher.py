# sources/fetching/fetcher.py
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .config import FetcherConfig
from .strategies.archive import ArchiveStrategy
from .strategies.base import ContentFetchStrategy
from .strategies.browser import BrowserStrategy
from .strategies.simple import SimpleHttpStrategy
from .strategy import FetchStrategy
from .types import ContentQuality, FetchResult

logger = logging.getLogger(__name__)


@dataclass
class FetchHistory:
    """Historical fetch results for a URL pattern"""

    pattern: str
    successful_strategies: dict[FetchStrategy, int] = field(
        default_factory=lambda: {strategy: 0 for strategy in FetchStrategy},
    )
    failed_strategies: dict[FetchStrategy, int] = field(
        default_factory=lambda: {strategy: 0 for strategy in FetchStrategy},
    )
    last_success: str | None = None
    last_failure: str | None = None

    def record_attempt(self, result: FetchResult, strategy: FetchStrategy):
        """Record fetch attempt results"""
        timestamp = datetime.now().isoformat()
        if result.content is not None and result.quality != ContentQuality.EMPTY:
            self.successful_strategies[strategy] += 1
            self.last_success = timestamp
        else:
            self.failed_strategies[strategy] += 1
            self.last_failure = timestamp


class StrategyManager:
    """Manages fetch strategies and their history"""

    def __init__(self, config: FetcherConfig):
        self.config = config
        self._pattern_history: dict[str, FetchHistory] = {}

    def get_url_pattern(self, url: str) -> str:
        """Extract pattern from URL for history tracking"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path_parts = parsed.path.split("/")[:3]  # Domain + first two path parts
        return f"{parsed.netloc}{''.join(path_parts)}"

    def get_optimal_strategy(self, url: str) -> FetchStrategy:
        """Determine best strategy based on history"""
        pattern = self.get_url_pattern(url)
        history = self._pattern_history.get(pattern)

        if history:
            # Find strategy with highest success rate
            strategy_scores = {}
            for strategy in FetchStrategy:
                successes = history.successful_strategies[strategy]
                failures = history.failed_strategies[strategy]
                total = successes + failures
                if total > 0:
                    score = successes / total
                    strategy_scores[strategy] = score

            if strategy_scores:
                return max(strategy_scores.items(), key=lambda x: x[1])[0]

        # Default to simple strategy if no history
        return FetchStrategy.SIMPLE

    def record_attempt(self, url: str, result: FetchResult, strategy: FetchStrategy):
        """Record attempt in history"""
        pattern = self.get_url_pattern(url)
        if pattern not in self._pattern_history:
            self._pattern_history[pattern] = FetchHistory(pattern)
        self._pattern_history[pattern].record_attempt(result, strategy)


class SmartContentFetcher:
    """Main content fetcher implementation"""

    def __init__(self, config: FetcherConfig | None = None):
        self.config = config or FetcherConfig()
        self.strategy_manager = StrategyManager(self.config)
        self.strategies: dict[FetchStrategy, ContentFetchStrategy] = {}
        self._init_strategies()

    def _init_strategies(self):
        """Initialize fetch strategies"""
        self.strategies = {
            FetchStrategy.SIMPLE: SimpleHttpStrategy(),
            FetchStrategy.BROWSER: BrowserStrategy(),
            FetchStrategy.ARCHIVE: ArchiveStrategy(),
        }

    async def fetch_content(self, url: str) -> FetchResult:
        """Fetch content using optimal strategy progression"""
        logger.debug(f"Starting fetch for {url}")
        strategy = self.strategy_manager.get_optimal_strategy(url)
        strategies_to_try = self._get_strategy_sequence(strategy)

        last_error = None
        for strategy_type in strategies_to_try:
            try:
                strategy_impl = self.strategies[strategy_type]
                logger.debug(f"Trying strategy {strategy_type.name} for {url}")
                result = await strategy_impl.fetch(url, self.config)
                self.strategy_manager.record_attempt(url, result, strategy_type)

                if result.success:
                    logger.debug(f"Success with {strategy_type.name} for {url}")
                    return result
                else:
                    logger.debug(
                        f"Strategy {strategy_type.name} failed for {url}: {result.error}",  # noqa: E501
                    )
                    last_error = result.error

            except Exception as e:
                logger.error(
                    f"Error in strategy {strategy_type.name} for {url}: {str(e)}",
                )
                last_error = str(e)
                self.strategy_manager.record_attempt(
                    url,
                    FetchResult(
                        content=None,
                        quality=ContentQuality.EMPTY,
                        strategy=strategy_type,
                        error=str(e),
                    ),
                    strategy_type,
                )

        # If we get here, all strategies failed
        return FetchResult(
            content=None,
            quality=ContentQuality.EMPTY,
            strategy=strategy,
            error=f"All strategies failed. Last error: {last_error}",
        )

    def _get_strategy_sequence(
        self,
        start_strategy: FetchStrategy,
    ) -> list[FetchStrategy]:
        """Get sequence of strategies to try"""
        # Order strategies based on starting point
        all_strategies = list(FetchStrategy)

        # Rotate list to start with chosen strategy
        start_idx = all_strategies.index(start_strategy)
        return all_strategies[start_idx:] + all_strategies[:start_idx]

    async def cleanup(self):
        """Cleanup all strategies"""
        for strategy in self.strategies.values():
            await strategy.cleanup()
