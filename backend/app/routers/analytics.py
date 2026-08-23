from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import (
    get_db,
)

from app.services.decision_analytics_service import (
    get_decision_funnel,
)

from app.services.provider_decision_analytics_service import (
    get_hospital_decision_analytics,
)

from app.services.hospital_decision_loss_service import (
    get_hospital_decision_loss,
)

from app.services.decision_feedback_analytics_service import (
    get_decision_feedback_summary,
    get_hospital_selection_reasons,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


# =========================================================
# 1. 전체 Decision Funnel
#
# GET /analytics/decision-funnel
# =========================================================

@router.get(
    "/decision-funnel"
)
def decision_funnel(
    db: Session = Depends(
        get_db
    ),
):

    return get_decision_funnel(
        db=db
    )


# =========================================================
# 2. 병원별 Decision Intelligence
#
# GET /analytics/hospitals
# =========================================================

@router.get(
    "/hospitals"
)
def hospital_decision_analytics(
    db: Session = Depends(
        get_db
    ),
):

    return (
        get_hospital_decision_analytics(
            db=db
        )
    )


# =========================================================
# 3. 병원별 Decision Loss Signals
#
# GET
# /analytics/hospitals/{hospital_id}/decision-loss
#
# 사용자가 실제로 다른 후보를 선택한 상황에서
# 관측된 차이를 분석한다.
#
# 이것은 causal reason이 아니라
# observed signal이다.
# =========================================================

@router.get(
    "/hospitals/{hospital_id}/decision-loss"
)
def hospital_decision_loss(
    hospital_id: int,
    db: Session = Depends(
        get_db
    ),
):

    result = (
        get_hospital_decision_loss(
            db=db,
            hospital_id=hospital_id,
        )
    )


    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital not found",
        )


    return result


# =========================================================
# 4. 전체 Decision Feedback Summary
#
# GET /analytics/decision-feedback-summary
#
#
# 사용자가 직접 밝힌:
#
# Selection Reasons
#
# PRICE
# AVAILABILITY
# LOCATION
# DATA_CONFIDENCE
# OTHER
#
#
# No-Selection Reasons
#
# BUDGET_TOO_HIGH
# TIME_NOT_MATCH
# LOCATION_NOT_MATCH
# INSUFFICIENT_INFORMATION
# OTHER
#
#
# 를 전체적으로 집계한다.
#
#
# 중요:
#
# 복수 선택이 가능하므로
# reason percentage의 합은
# 100%를 초과할 수 있다.
# =========================================================

@router.get(
    "/decision-feedback-summary"
)
def decision_feedback_summary(
    db: Session = Depends(
        get_db
    ),
):

    return (
        get_decision_feedback_summary(
            db=db
        )
    )


# =========================================================
# 5. 특정 병원의 실제 선택 이유
#
# GET
# /analytics/hospitals/{hospital_id}/selection-reasons
#
#
# 해당 병원의 Candidate가 실제 SELECTED되고
# 사용자가 직접 제출한 SELECTION_REASON만 집계한다.
#
#
# 중요:
#
# NO_SELECTION_REASON은
# candidate_match_id가 NULL이기 때문에
# 특정 병원 탓으로 귀속하지 않는다.
# =========================================================

@router.get(
    "/hospitals/{hospital_id}/selection-reasons"
)
def hospital_selection_reasons(
    hospital_id: int,
    db: Session = Depends(
        get_db
    ),
):

    return (
        get_hospital_selection_reasons(
            db=db,
            hospital_id=hospital_id,
        )
    )