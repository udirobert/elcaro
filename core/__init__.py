"""Core Elcaro IPI detection engine.

Public API:
    from core import IpiDetectionEngine, ScanRequest, ScanResponse
    engine = IpiDetectionEngine()
    result = engine.scan(ScanRequest(content="...", content_type="email"))
"""

from core.schemas import (
    ContentType,
    DetectionIndicator,
    RiskLevel,
    ScanRequest,
    ScanResponse,
    TechniqueClass,
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
]
