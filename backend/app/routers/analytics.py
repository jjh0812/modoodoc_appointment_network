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
#
# 전체 검색 흐름:
#
# SEARCHED
#     ↓
# SHOWN
#     ↓
# SELECTED
#     ↓
# HELD
#     ↓
# CONFIRMED
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
#
# 각 병원이:
#
# 몇 번 노출됐는지
#     ↓
# 몇 번 선택됐는지
#     ↓
# 몇 번 HOLD됐는지
#     ↓
# 몇 번 예약됐는지
#
# 분석한다.
#
#
# 주의:
#
# 이 값은 의료 품질 점수가 아니다.
#
# Patient Intent와
# Transaction Graph에서 발생한
# 행동 데이터다.
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
#
# 질문:
#
# "이 병원은 후보로 노출됐는데
#  다른 병원이 선택된 순간,
#  어떤 차이가 관측됐는가?"
#
#
# 예:
#
# NOT_TOP1
#
# LOWER_RANK_THAN_SELECTED
#
# LOWER_SCORE_THAN_SELECTED
#
# BUDGET_PARTIAL_MATCH
#
#
# 중요:
#
# 이것은 '선택되지 않은 진짜 원인'을
# 증명하는 causal analysis가 아니다.
#
# 실제 선택 시점에 관측된
# Decision Loss Signal을 분석한다.
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


    # =====================================================
    # 존재하지 않는 병원
    # =====================================================

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital not found",
        )


    return result