from sqlalchemy.exc import (
    IntegrityError,
)

from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentSlot,
    DecisionEvent,
    SlotHold,
)

from app.services.hold_service import (
    release_expired_hold,
)


# =========================================================
# Appointment Core Error
#
# FastAPI와 MCP가 같은 Core를 사용하기 때문에
# service 안에서는 HTTPException을 직접 사용하지 않는다.
# =========================================================

class AppointmentServiceError(Exception):

    def __init__(
        self,
        status_code: int,
        detail: str,
    ):

        self.status_code = (
            status_code
        )

        self.detail = (
            detail
        )

        super().__init__(
            detail
        )


# =========================================================
# HOLD → CONFIRMED Core Service
#
# FastAPI와 MCP가 모두 이 함수를 사용한다.
# =========================================================

def confirm_slot_hold(
    db: Session,
    hold_id: int,
    idempotency_key: str,
):

    try:

        # =================================================
        # 1. 빠른 Idempotency 확인
        #
        # 같은 transaction이 이미 처리됐다면
        # Appointment를 새로 만들지 않는다.
        # =================================================

        existing_appointment = (
            db.query(
                Appointment
            )
            .filter(
                Appointment.idempotency_key
                == idempotency_key
            )
            .first()
        )


        if existing_appointment is not None:

            # ---------------------------------------------
            # 같은 key가 전혀 다른 HOLD에 사용됨
            # ---------------------------------------------

            if (
                existing_appointment.hold_id
                != hold_id
            ):

                raise AppointmentServiceError(
                    status_code=409,
                    detail=(
                        "Idempotency key already used "
                        "for another hold"
                    ),
                )


            # ---------------------------------------------
            # 같은 transaction retry
            # ---------------------------------------------

            db.commit()

            return existing_appointment


        # =================================================
        # 2. HOLD snapshot
        #
        # 어떤 Slot을 잠가야 하는지 알아낸다.
        # =================================================

        hold_snapshot = (
            db.query(
                SlotHold
            )
            .filter(
                SlotHold.id
                == hold_id
            )
            .first()
        )


        if hold_snapshot is None:

            raise AppointmentServiceError(
                status_code=404,
                detail="Hold not found",
            )


        # =================================================
        # 3. Slot ROW LOCK
        #
        # SELECT ... FOR UPDATE
        # =================================================

        slot = (
            db.query(
                AppointmentSlot
            )
            .filter(
                AppointmentSlot.id
                == hold_snapshot.slot_id
            )
            .with_for_update()
            .first()
        )


        if slot is None:

            raise AppointmentServiceError(
                status_code=404,
                detail="Slot not found",
            )


        # =================================================
        # 4. HOLD ROW LOCK
        # =================================================

        hold = (
            db.query(
                SlotHold
            )
            .filter(
                SlotHold.id
                == hold_id
            )
            .with_for_update()
            .first()
        )


        if hold is None:

            raise AppointmentServiceError(
                status_code=404,
                detail="Hold not found",
            )


        # =================================================
        # 5. LOCK을 기다리는 사이에
        # 다른 요청이 Appointment를 만들었을 수 있으므로
        # Idempotency 다시 확인
        # =================================================

        existing_appointment = (
            db.query(
                Appointment
            )
            .filter(
                Appointment.idempotency_key
                == idempotency_key
            )
            .first()
        )


        if existing_appointment is not None:

            if (
                existing_appointment.hold_id
                != hold_id
            ):

                raise AppointmentServiceError(
                    status_code=409,
                    detail=(
                        "Idempotency key already used "
                        "for another hold"
                    ),
                )


            db.commit()

            return existing_appointment


        # =================================================
        # 6. HOLD 만료 확인
        #
        # 만료되었다면:
        #
        # ACTIVE → EXPIRED
        # HELD   → AVAILABLE
        # =================================================

        released = (
            release_expired_hold(
                slot=slot,
                db=db,
            )
        )


        if released:

            # EXPIRED 상태는 실제 DB에 남긴다.
            db.commit()

            raise AppointmentServiceError(
                status_code=409,
                detail="Hold is not active",
            )


        # =================================================
        # 7. HOLD 상태 확인
        # =================================================

        if hold.status != "ACTIVE":

            raise AppointmentServiceError(
                status_code=409,
                detail="Hold is not active",
            )


        # =================================================
        # 8. Slot 상태 확인
        # =================================================

        if slot.status != "HELD":

            raise AppointmentServiceError(
                status_code=409,
                detail="Slot is not held",
            )


        # =================================================
        # 9. Transaction Graph 연결 찾기
        #
        # Candidate-aware HOLD였다면:
        #
        # SHOWN
        # → SELECTED
        # → HELD
        #
        # event가 이미 존재한다.
        #
        # hold_id를 이용해서 해당 Graph를 찾는다.
        # =================================================

        graph_held_event = (
            db.query(
                DecisionEvent
            )
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


        # =================================================
        # 10. Appointment 생성
        # =================================================

        appointment = Appointment(

            slot_id=
                slot.id,

            hold_id=
                hold.id,

            source=
                hold.source,

            idempotency_key=
                idempotency_key,

            status=
                "CONFIRMED",
        )


        db.add(
            appointment
        )


        # =================================================
        # 11. Slot / Hold 상태 확정
        # =================================================

        slot.status = (
            "CONFIRMED"
        )

        hold.status = (
            "CONFIRMED"
        )


        # =================================================
        # 12. INSERT 먼저 전달
        #
        # Appointment ID가 필요하지만
        # transaction은 아직 끝내지 않는다.
        # =================================================

        db.flush()


        # =================================================
        # 13. Transaction Graph
        #
        # Candidate Search에서 시작한 예약인 경우
        # CONFIRMED event 추가
        # =================================================

        if graph_held_event is not None:

            confirmed_event = (
                DecisionEvent(

                    intent_id=
                        graph_held_event
                        .intent_id,

                    candidate_match_id=
                        graph_held_event
                        .candidate_match_id,

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
                            idempotency_key,
                    },
                )
            )


            db.add(
                confirmed_event
            )


        # =================================================
        # 14. 최종 COMMIT
        #
        # Appointment 생성
        # Slot CONFIRMED
        # Hold CONFIRMED
        # DecisionEvent CONFIRMED
        #
        # 모두 하나의 transaction
        # =================================================

        try:

            db.commit()


        # =================================================
        # 15. DB UNIQUE constraint
        #
        # 극단적인 race의 마지막 방어선
        # =================================================

        except IntegrityError:

            db.rollback()


            existing_appointment = (
                db.query(
                    Appointment
                )
                .filter(
                    Appointment.idempotency_key
                    == idempotency_key
                )
                .first()
            )


            if (
                existing_appointment is not None
                and
                existing_appointment.hold_id
                == hold_id
            ):

                db.commit()

                return existing_appointment


            raise AppointmentServiceError(
                status_code=409,
                detail="Appointment conflict",
            )


        return appointment


    # =====================================================
    # 예상한 business error
    # =====================================================

    except AppointmentServiceError:

        # 만료 처리를 commit한 경우에는
        # rollback해도 이미 확정된 상태는 유지된다.
        db.rollback()

        raise


    # =====================================================
    # 예상하지 못한 오류
    # =====================================================

    except Exception:

        db.rollback()

        raise