"""Compatibility re-exports for identity DTOs.

Canonical DTO definitions live in soorma_common.models.
"""

from soorma_common.models import (
    DelegatedIssuerRequest,
    DelegatedIssuerResponse,
    MappingEvaluationRequest,
    MappingEvaluationResponse,
    OnboardingRequest,
    OnboardingResponse,
    PrincipalRequest,
    PrincipalResponse,
    TokenIssueRequest,
    TokenIssueResponse,
)

__all__ = [
    "OnboardingRequest",
    "OnboardingResponse",
    "PrincipalRequest",
    "PrincipalResponse",
    "TokenIssueRequest",
    "TokenIssueResponse",
    "DelegatedIssuerRequest",
    "DelegatedIssuerResponse",
    "MappingEvaluationRequest",
    "MappingEvaluationResponse",
]
