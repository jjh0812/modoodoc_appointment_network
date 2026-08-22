from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


# =========================================================
# 사용자가 후보를 선택한 이유
# =========================================================

SelectionReasonCode = Literal[
    "PRICE",
    "AVAILABILITY",
    "LOCATION",
    "DATA_CONFIDENCE",
    "OTHER",
]


# =========================================================
# 아무 후보도 선택하지 않은 이유
# =========================================================

NoSelectionReasonCode = Literal[
    "BUDGET_TOO_HIGH",
    "TIME_NOT_MATCH",
    "LOCATION_NOT_MATCH",
    "INSUFFICIENT_INFORMATION",
    "OTHER",
]


# =========================================================
# Selection Feedback
# =========================================================

class SelectionFeedbackRequest(
    BaseModel
):

    intent_id: int

    candidate_match_id: int

    reason_codes: list[
        SelectionReasonCode
    ] = Field(
        min_length=1,
    )

    free_text: str | None = None

    source: str = (
        "AI_SIMULATOR"
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=120,
    )


# =========================================================
# No Selection Feedback
# =========================================================

class NoSelectionFeedbackRequest(
    BaseModel
):

    intent_id: int

    reason_codes: list[
        NoSelectionReasonCode
    ] = Field(
        min_length=1,
    )

    free_text: str | None = None

    source: str = (
        "AI_SIMULATOR"
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=120,
    )


# =========================================================
# Response
# =========================================================

class DecisionFeedbackResponse(
    BaseModel
):

    id: int

    intent_id: int

    candidate_match_id: int | None

    feedback_type: str

    reason_codes: list[str]

    free_text: str | None

    source: str

    idempotency_key: str


    model_config = {
        "from_attributes": True,
    }