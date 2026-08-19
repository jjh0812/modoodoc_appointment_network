from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppointmentSlot
from app.schemas import AppointmentSlotResponse

from app.services.hold_service import (
    release_expired_hold,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/providers",
    tags=["availability"],
)


# =========================================================
# 의사의 AVAILABLE 예약시간 조회
#
# 예:
# GET /providers/1/availability
# =========================================================

@router.get(
    "/{provider_id}/availability",
    response_model=list[AppointmentSlotResponse],
)
def get_availability(
    provider_id: int,
    db: Session = Depends(get_db),
):

    # -----------------------------------------------------
    # 1. 이 의사의 HELD 슬롯들을 먼저 찾는다.
    #
    # 이유:
    # 5분이 지난 HOLD가 아직 DB에 HELD로
    # 남아 있을 수 있기 때문
    # -----------------------------------------------------

    held_slots = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.provider_id == provider_id,
            AppointmentSlot.status == "HELD",
        )
        .all()
    )


    # -----------------------------------------------------
    # 2. 실제로 만료 처리가 발생했는지 기록
    # -----------------------------------------------------

    expired_hold_found = False


    # -----------------------------------------------------
    # 3. 각각의 HOLD가 만료됐는지 검사
    #
    # 만료됐다면:
    #
    # SlotHold
    # ACTIVE → EXPIRED
    #
    # AppointmentSlot
    # HELD → AVAILABLE
    # -----------------------------------------------------

    for slot in held_slots:

        released = release_expired_hold(
            slot=slot,
            db=db,
        )

        if released:
            expired_hold_found = True


    # -----------------------------------------------------
    # 4. 실제 만료된 HOLD가 있었다면
    #    변경 내용을 최종 저장
    #
    # hold_service에서는 flush까지만 하고
    # 여기서 transaction을 끝낸다.
    # -----------------------------------------------------

    if expired_hold_found:

        db.commit()


    # -----------------------------------------------------
    # 5. 만료 정리가 끝난 뒤
    #    실제 AVAILABLE 슬롯만 다시 조회
    # -----------------------------------------------------

    available_slots = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.provider_id == provider_id,
            AppointmentSlot.status == "AVAILABLE",
        )
        .order_by(
            AppointmentSlot.start_time
        )
        .all()
    )


    # -----------------------------------------------------
    # 6. 외부 AI / 사용자에게 반환
    # -----------------------------------------------------

    return available_slots