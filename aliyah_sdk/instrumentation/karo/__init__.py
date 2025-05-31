"""
Ops Instrumentor for the Karo Agent Framework.

This module provides automatic instrumentation for the Karo framework when Ops is imported.
It traces key operations like agent runs, tool executions, and memory interactions.
"""

import logging

logger = logging.getLogger(__name__)

def get_version() -> str:
    """Get the version of the Karo SDK, or 'unknown' if not found"""
    try:
        # Assuming 'karo' is the installed package name
        from importlib.metadata import version
        return version("karo")
    except ImportError:
        # This case shouldn't happen if instrumentation_dependencies check passes
        logger.debug("Could not import 'karo' package to determine version.")
        return "unknown"
    except Exception as e:
        logger.debug(f"Error getting 'karo' package version: {e}")
        return "unknown"

LIBRARY_NAME = "karo"
LIBRARY_VERSION: str = get_version()

# Import after defining constants to avoid circular imports
from .instrumentor import KaroInstrumentor # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "KaroInstrumentor",
]