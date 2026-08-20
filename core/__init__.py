"""Core Elcaro IPI detection engine.

Public API:
    from core import IpiDetectionEngine, ScanRequest, ScanResponse
    engine = IpiDetectionEngine()
    result = engine.scan(ScanRequest(content="...", content_type="email"))
"""

from core.schemas import (
    INJECTION_THRESHOLD,
    SUPPORTED_INTENTS,
    ContentType,
    DetectionIndicator,
    RiskLevel,
    ScanRequest,
    ScanResponse,
    TechniqueClass,
    TelegraphAnswer,
    TelegraphQueryRequest,
    TelegraphQueryResponse,
)
from core.taxonomy import IpiDetectionEngine

__all__ = [
    "IpiDetectionEngine",
    "ScanRequest",
    "ScanResponse",
    "ContentType",
    "RiskLevel",
    "TechniqueClass",
    "DetectionIndicator",
    "TelegraphQueryRequest",
    "TelegraphQueryResponse",
    "TelegraphAnswer",
    "INJECTION_THRESHOLD",
    "SUPPORTED_INTENTS",
]
