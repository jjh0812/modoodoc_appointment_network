from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import (
    get_db,
)

from app.schemas import (
    SlotHoldRequest,
    SlotHoldResponse,
)

from app.services.hold_service import (
    HoldServiceError,
    create_slot_hold,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/slots",
    tags=["holds"],
)


# =========================================================
# 예약 슬롯 HOLD
#
# 이 Router는 실제 HOLD 규칙을 직접 구현하지 않는다.
#
# 실제 business logic:
#
# app/services/hold_service.py
#     ↓
# create_slot_hold()
#
#
# 이유:
#
# FastAPI
# MCP
#
# 둘 다 같은 HOLD Core를 사용하게 하기 위해서.
# =========================================================


# =========================================================
# 기존 직접 HOLD
#
# POST /slots/3/hold
#
# {
#     "source": "ChatGPT"
# }
#
#
# Candidate-aware HOLD
#
# POST /slots/3/hold
#
# {
#     "source": "AI_SIMULATOR",
#     "candidate_match_id": 61
# }
# =========================================================

@router.post(
    "/{slot_id}/hold",
    response_model=SlotHoldResponse,
)
def hold_slot(
    slot_id: int,
    request: SlotHoldRequest,
    db: Session = Depends(get_db),
):

    try:

        # -------------------------------------------------
        # 실제 HOLD Core Service 호출
        #
        # 여기 안에서:
        #
        # Candidate 검증
        #       ↓
        # PostgreSQL FOR UPDATE
        #       ↓
        # AVAILABLE 확인
        #       ↓
        # SELECTED event
        #       ↓
        # SlotHold 생성
        #       ↓
        # HELD event
        #       ↓
        # COMMIT
        #
        # 이 모두 처리된다.
        # -------------------------------------------------

        return create_slot_hold(

            db=db,

            slot_id=
                slot_id,

            source=
                request.source,

            candidate_match_id=
                request.candidate_match_id,
        )


    except HoldServiceError as error:

        # -------------------------------------------------
        # Core Service의 business error를
        # HTTP 응답으로 변환
        #
        # 예:
        #
        # Slot 없음
        # → 404
        #
        # Candidate / Slot 불일치
        # → 409
        #
        # 이미 HOLD된 Slot
        # → 409
        # -------------------------------------------------

        raise HTTPException(

            status_code=
                error.status_code,

            detail=
                error.detail,
        )