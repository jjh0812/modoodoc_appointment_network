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
    DecisionEvent,
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
#
# POST /holds/{hold_id}/confirm
#
# {
#     "idempotency_key": "booking-001"
# }
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

    # =====================================================
    # 1. 빠른 Idempotency 확인
    #
    # 이미 같은 요청이 성공했다면
    # Appointment를 새로 만들지 않는다.
    # =====================================================

    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == request.idempotency_key
        )
        .first()
    )


    if existing_appointment is not None:

        # -------------------------------------------------
        # 같은 key를 전혀 다른 HOLD에 재사용
        # -------------------------------------------------

        if (
            existing_appointment.hold_id
            != hold_id
        ):

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Idempotency key already used "
                    "for another hold"
                ),
            )


        # -------------------------------------------------
        # 같은 예약의 retry
        #
        # 이미 CONFIRMED event도 첫 transaction에서
        # 함께 저장됐으므로 새 이벤트를 만들지 않는다.
        # -------------------------------------------------

        db.commit()

        return existing_appointment


    # =====================================================
    # 2. HOLD snapshot 조회
    #
    # 어떤 Slot을 잠가야 하는지 알아내기 위함
    # =====================================================

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


    # =====================================================
    # 3. Slot ROW LOCK
    #
    # SELECT ... FOR UPDATE
    #
    # 같은 예약을 동시에 확정하려는 요청을
    # PostgreSQL이 직렬화한다.
    # =====================================================

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


    # =====================================================
    # 4. HOLD ROW LOCK
    # =====================================================

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


    # =====================================================
    # 5. LOCK을 기다리는 동안
    # 다른 요청이 Appointment를 만들었을 수 있음
    #
    # 그래서 idempotency를 다시 확인
    # =====================================================

    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == request.idempotency_key
        )
        .first()
    )


    if existing_appointment is not None:

        if (
            existing_appointment.hold_id
            != hold_id
        ):

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Idempotency key already used "
                    "for another hold"
                ),
            )


        db.commit()

        return existing_appointment


    # =====================================================
    # 6. HOLD 만료 여부 확인
    #
    # 만료됐다면:
    #
    # ACTIVE → EXPIRED
    # HELD   → AVAILABLE
    # =====================================================

    released = release_expired_hold(
        slot=slot,
        db=db,
    )


    if released:

        db.commit()

        raise HTTPException(
            status_code=409,
            detail="Hold is not active",
        )


    # =====================================================
    # 7. HOLD 상태 확인
    # =====================================================

    if hold.status != "ACTIVE":

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Hold is not active",
        )


    # =====================================================
    # 8. Slot 상태 확인
    # =====================================================

    if slot.status != "HELD":

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Slot is not held",
        )


    # =====================================================
    # 9. 이 HOLD가 Transaction Graph에서 시작된 것인지 확인
    #
    # Candidate-aware HOLD였다면 앞에서:
    #
    # SHOWN
    # → SELECTED
    # → HELD
    #
    # 이벤트가 이미 존재한다.
    #
    # HELD event의 hold_id를 이용해
    # 어떤 Intent / Candidate인지 다시 찾는다.
    # =====================================================

    graph_held_event = (
        db.query(DecisionEvent)
        .filter(
            DecisionEvent.hold_id
            == hold.id,

            DecisionEvent.event_type
            == "HELD",
        )
        .order_by(
            DecisionEvent.id.desc()
        )
        .first()
    )


    # =====================================================
    # 10. 실제 Appointment 생성
    # =====================================================

    appointment = Appointment(

        slot_id=
            slot.id,

        hold_id=
            hold.id,

        source=
            hold.source,

        idempotency_key=
            request.idempotency_key,

        status=
            "CONFIRMED",
    )


    db.add(
        appointment
    )


    # =====================================================
    # 11. HOLD / SLOT도 CONFIRMED로 변경
    # =====================================================

    hold.status = "CONFIRMED"

    slot.status = "CONFIRMED"


    # =====================================================
    # 12. Appointment ID 확보 + CONFIRMED Event 생성
    #
    # flush는 COMMIT이 아니다.
    #
    # Appointment INSERT를 DB에 전달해서
    # appointment.id를 얻지만
    # transaction / ROW LOCK은 계속 유지한다.
    # =====================================================

    try:

        db.flush()


        # -------------------------------------------------
        # Candidate Search에서 시작한 예약인 경우만
        # Transaction Graph에 CONFIRMED 추가
        # -------------------------------------------------

        if graph_held_event is not None:

            confirmed_event = DecisionEvent(

                intent_id=
                    graph_held_event.intent_id,

                candidate_match_id=
                    graph_held_event.candidate_match_id,

                event_type=
                    "CONFIRMED",

                slot_id=
                    slot.id,

                hold_id=
                    hold.id,

                appointment_id=
                    appointment.id,

                event_metadata={
                    "source":
                        hold.source,

                    "idempotency_key":
                        request.idempotency_key,
                },
            )


            db.add(
                confirmed_event
            )


        # =================================================
        # 13. 최종 COMMIT
        #
        # 아래가 한 transaction으로 저장:
        #
        # Appointment 생성
        # Slot      → CONFIRMED
        # Hold      → CONFIRMED
        # Event     → CONFIRMED
        #
        # 그리고 ROW LOCK 해제
        # =================================================

        db.commit()


    # =====================================================
    # 14. DB UNIQUE constraint 마지막 방어선
    #
    # 극단적인 race에서도
    # idempotency_key 중복 INSERT 방지
    # =====================================================

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
            and existing_appointment.hold_id
            == hold_id
        ):

            db.commit()

            return existing_appointment


        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Appointment conflict",
        )


    # =====================================================
    # 15. 결과 반환
    #
    # expire_on_commit=False이므로
    # db.refresh() 필요 없음
    # =====================================================

    return appointment