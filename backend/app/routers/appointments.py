from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db

from app.models import (
    Appointment,
    AppointmentSlot,
    SlotHold,
)

from app.schemas import (
    AppointmentConfirmRequest,
    AppointmentResponse,
)

from app.services.hold_service import (
    release_expired_hold,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/holds",
    tags=["appointments"],
)


# =========================================================
# HOLD → 실제 예약 확정
# =========================================================

@router.post(
    "/{hold_id}/confirm",
    response_model=AppointmentResponse,
)
def confirm_appointment(
    hold_id: int,
    request: AppointmentConfirmRequest,
    db: Session = Depends(get_db),
):

    # -----------------------------------------------------
    # 1. 빠른 idempotency 확인
    # -----------------------------------------------------

    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == request.idempotency_key
        )
        .first()
    )


    if existing_appointment is not None:

        # 같은 key를 다른 HOLD에 사용한 경우
        if existing_appointment.hold_id != hold_id:

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Idempotency key already used "
                    "for another hold"
                ),
            )


        # -------------------------------------------------
        # 중요:
        #
        # SELECT로 시작된 transaction을
        # 응답 전에 끝낸다.
        #
        # DB connection을 즉시 pool로 반환
        # -------------------------------------------------

        db.commit()

        return existing_appointment


    # -----------------------------------------------------
    # 2. HOLD snapshot 조회
    # -----------------------------------------------------

    hold_snapshot = (
        db.query(SlotHold)
        .filter(
            SlotHold.id == hold_id
        )
        .first()
    )


    if hold_snapshot is None:

        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Hold not found",
        )


    # -----------------------------------------------------
    # 3. Slot ROW LOCK
    #
    # SELECT ... FOR UPDATE
    # -----------------------------------------------------

    slot = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id
            == hold_snapshot.slot_id
        )
        .with_for_update()
        .first()
    )


    if slot is None:

        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Slot not found",
        )


    # -----------------------------------------------------
    # 4. HOLD ROW LOCK
    # -----------------------------------------------------

    hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.id == hold_id
        )
        .with_for_update()
        .first()
    )


    if hold is None:

        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Hold not found",
        )


    # -----------------------------------------------------
    # 5. LOCK 기다리는 동안
    #    다른 요청이 Appointment를 만들었을 수 있음
    #
    # 그래서 다시 idempotency 검사
    # -----------------------------------------------------

    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == request.idempotency_key
        )
        .first()
    )


    if existing_appointment is not None:

        if existing_appointment.hold_id != hold_id:

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Idempotency key already used "
                    "for another hold"
                ),
            )


        # transaction 종료
        # → ROW LOCK 해제
        # → connection 반환
        db.commit()

        return existing_appointment


    # -----------------------------------------------------
    # 6. HOLD 만료 여부 확인
    # -----------------------------------------------------

    released = release_expired_hold(
        slot=slot,
        db=db,
    )


    # -----------------------------------------------------
    # 만료된 HOLD였다면
    # EXPIRED 상태를 실제 DB에 저장한 뒤 거절
    # -----------------------------------------------------

    if released:

        db.commit()

        raise HTTPException(
            status_code=409,
            detail="Hold is not active",
        )


    # -----------------------------------------------------
    # 7. HOLD 상태 확인
    # -----------------------------------------------------

    if hold.status != "ACTIVE":

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Hold is not active",
        )


    # -----------------------------------------------------
    # 8. SLOT 상태 확인
    # -----------------------------------------------------

    if slot.status != "HELD":

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Slot is not held",
        )


    # -----------------------------------------------------
    # 9. Appointment 생성
    # -----------------------------------------------------

    appointment = Appointment(
        slot_id=slot.id,
        hold_id=hold.id,
        source=hold.source,
        idempotency_key=request.idempotency_key,
        status="CONFIRMED",
    )

    db.add(
        appointment
    )


    # -----------------------------------------------------
    # 10. HOLD / SLOT 확정
    # -----------------------------------------------------

    hold.status = "CONFIRMED"

    slot.status = "CONFIRMED"


    # -----------------------------------------------------
    # 11. 최종 COMMIT
    #
    # 여기서 ROW LOCK 해제
    # connection도 pool로 반환
    # -----------------------------------------------------

    try:

        db.commit()


    # -----------------------------------------------------
    # UNIQUE constraint
    # 마지막 방어선
    # -----------------------------------------------------

    except IntegrityError:

        db.rollback()


        existing_appointment = (
            db.query(Appointment)
            .filter(
                Appointment.idempotency_key
                == request.idempotency_key
            )
            .first()
        )


        if (
            existing_appointment is not None
            and existing_appointment.hold_id == hold_id
        ):

            # SELECT transaction도 종료
            db.commit()

            return existing_appointment


        # 위 SELECT가 만든 transaction 정리
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Appointment conflict",
        )


    # -----------------------------------------------------
    # 중요:
    #
    # 기존:
    #
    # db.commit()
    # db.refresh(appointment)  ← 다시 DB connection 필요
    #
    # 수정:
    #
    # db.commit()
    # return appointment
    #
    # expire_on_commit=False이므로
    # 다시 SELECT할 필요 없음
    # -----------------------------------------------------

    return appointment