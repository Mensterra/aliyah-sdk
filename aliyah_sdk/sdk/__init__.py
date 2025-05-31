"""
Aaliyah SDK for tracing and monitoring AI agents.

This module provides a high-level API for creating and managing spans
for different types of operations in AI agent workflows.
"""

# Import core components
from aliyah_sdk.sdk.core import TracingCore

# Import decorators
from aliyah_sdk.sdk.decorators import agent, operation, session, task, workflow

# from aaliyah.sdk.traced import TracedObject  # Merged into TracedObject
from aliyah_sdk.sdk.types import TracingConfig

__all__ = [
    # Core components
    "TracingCore",
    "TracingConfig",
    # Decorators
    "session",
    "operation",
    "agent",
    "task",
    "workflow",
]
