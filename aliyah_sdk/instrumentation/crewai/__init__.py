"""OpenTelemetry CrewAI instrumentation"""

from aliyah_sdk.instrumentation.crewai.version import __version__
from aliyah_sdk.instrumentation.crewai.instrumentation import CrewAIInstrumentor

__all__ = ["CrewAIInstrumentor", "__version__"]
