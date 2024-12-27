# core/logging/logger.py

import logging
import uuid
from functools import wraps
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from contextlib import contextmanager


@dataclass
class ProcessContext:
    """Tracks processing context for workflow logging"""

    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    component: str = ""
    start_time: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class WorkflowLogger:
    """Logger that maintains context for tracking workflows through the system"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = None

        # Create a separate logger for workflow events
        self.workflow_logger = logging.getLogger(f"{name}.workflow")

        # Setup default handler if none exists (for testing environment)
        root_logger = logging.getLogger("topic_engine")
        if not root_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(workflow_id)s%(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            handler.set_name("workflow_file")
            root_logger.addHandler(handler)

        # Get or create workflow handler
        workflow_handler = next(
            (
                h
                for h in root_logger.handlers
                if getattr(h, "get_name", lambda: "")() == "workflow_file"
            ),
            root_logger.handlers[0] if root_logger.handlers else None,
        )

        if workflow_handler and not any(
            h.get_name() == "workflow_file" for h in self.workflow_logger.handlers
        ):
            self.workflow_logger.addHandler(workflow_handler)

    def _get_extra(self, extra: Optional[Dict] = None) -> Dict:
        """Prepare extra dict with workflow context if available"""
        extra_dict = extra.copy() if extra else {}
        if self.context:
            extra_dict["workflow_id"] = f"[{self.context.workflow_id}] "
            if self.context.metadata:
                extra_dict.update(self.context.metadata)
        else:
            extra_dict["workflow_id"] = ""  # Ensure this is always present
        return extra_dict

    def debug(self, message: str, **kwargs):
        extra = self._get_extra(kwargs)
        if self.context:
            self.workflow_logger.debug(message, extra=extra)
        else:
            self.logger.debug(message, extra=extra)

    def info(self, message: str, **kwargs):
        extra = self._get_extra(kwargs)
        if self.context:
            self.workflow_logger.info(message, extra=extra)
        else:
            self.logger.info(message, extra=extra)

    def warning(self, message: str, **kwargs):
        extra = self._get_extra(kwargs)
        if self.context:
            self.workflow_logger.warning(message, extra=extra)
        else:
            self.logger.warning(message, extra=extra)

    def error(self, message: str, **kwargs):
        extra = self._get_extra(kwargs)
        if self.context:
            self.workflow_logger.error(message, extra=extra)
        else:
            self.logger.error(message, extra=extra)

    def critical(self, message: str, **kwargs):
        extra = self._get_extra(kwargs)
        if self.context:
            self.workflow_logger.critical(message, extra=extra)
        else:
            self.logger.critical(message, extra=extra)

    @contextmanager
    def workflow_context(self, component: str, **metadata):
        """Context manager for tracking workflow processing"""
        previous_context = self.context
        self.context = ProcessContext(component=component, metadata=metadata)
        try:
            self.debug(f"Starting {component} workflow", **metadata)
            yield self.context
        finally:
            duration = time.time() - self.context.start_time
            self.debug(f"Completed {component} workflow", duration=f"{duration:.2f}s", **metadata)
            self.context = previous_context


def get_logger(name: str) -> WorkflowLogger:
    """Get a workflow-aware logger for a component"""
    return WorkflowLogger(name)
