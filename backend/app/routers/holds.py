from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models import (
    AppointmentSlot,
    SlotHold,
)

from app.schemas import (
    SlotHoldRequest,
    SlotHoldResponse,
)

from app.services.hold_service import (
    release_expired_hold,
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
# 예:
#
# POST /slots/1/hold
#
# {
#     "source": "ChatGPT"
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

    # -----------------------------------------------------
    # 1. 해당 예약 슬롯 찾기 + ROW LOCK
    #
    # SELECT ... FOR UPDATE
    #
    # 이 transaction이 끝날 때까지
    # 다른 transaction은 같은 슬롯을
    # 동시에 수정할 수 없다.
    # -----------------------------------------------------

    slot = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id == slot_id
        )
        .with_for_update()
        .first()
    )


    # -----------------------------------------------------
    # 2. 슬롯 자체가 없으면 404
    # -----------------------------------------------------

    if slot is None:

        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Slot not found",
        )


    # -----------------------------------------------------
    # 3. 기존 HOLD가 만료됐는지 확인
    #
    # 만료됐다면:
    #
    # ACTIVE → EXPIRED
    # HELD   → AVAILABLE
    #
    # 여기서는 아직 COMMIT하지 않는다.
    # ROW LOCK을 계속 유지한다.
    # -----------------------------------------------------

    release_expired_hold(
        slot=slot,
        db=db,
    )


    # -----------------------------------------------------
    # 4. AVAILABLE인지 확인
    #
    # 다른 요청이 먼저 HOLD했다면
    # 여기에서 409
    # -----------------------------------------------------

    if slot.status != "AVAILABLE":

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Slot is not available",
        )


    # -----------------------------------------------------
    # 5. 새 HOLD 만료시간 계산
    # -----------------------------------------------------

    expires_at = (
        datetime.utcnow()
        + timedelta(minutes=5)
    )


    # -----------------------------------------------------
    # 6. 슬롯 상태 변경
    #
    # AVAILABLE → HELD
    # -----------------------------------------------------

    slot.status = "HELD"


    # -----------------------------------------------------
    # 7. 새로운 HOLD 기록 생성
    # -----------------------------------------------------

    hold = SlotHold(
        slot_id=slot.id,
        source=request.source,
        expires_at=expires_at,
        status="ACTIVE",
    )

    db.add(hold)


    # -----------------------------------------------------
    # 8. 최종 저장
    #
    # 이 COMMIT이 완료되는 순간
    # ROW LOCK도 풀린다.
    # -----------------------------------------------------

    db.commit()

    db.refresh(hold)


    # -----------------------------------------------------
    # 9. HOLD 결과 반환
    # -----------------------------------------------------

    return hold