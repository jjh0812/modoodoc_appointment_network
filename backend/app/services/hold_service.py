from datetime import (
    datetime,
    timedelta,
)

from sqlalchemy.orm import Session

from app.models import (
    AppointmentSlot,
    CandidateMatch,
    DecisionEvent,
    SlotHold,
)


# =========================================================
# HOLD Core Error
#
# FastAPI와 MCP가 같은 service를 사용하므로
# HTTPException을 service 안에서 직접 사용하지 않는다.
# =========================================================

class HoldServiceError(Exception):

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
# 만료된 HOLD가 있으면 해제
# =========================================================

def release_expired_hold(
    slot: AppointmentSlot,
    db: Session,
):

    # -----------------------------------------------------
    # HELD 상태가 아니면 확인할 필요 없음
    # -----------------------------------------------------

    if slot.status != "HELD":

        return False


    # -----------------------------------------------------
    # 현재 ACTIVE HOLD 찾기
    # -----------------------------------------------------

    hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.slot_id
            == slot.id,

            SlotHold.status
            == "ACTIVE",
        )
        .first()
    )


    if hold is None:

        return False


    now = (
        datetime.utcnow()
    )


    # 아직 HOLD 시간이 남음
    if hold.expires_at > now:

        return False


    # -----------------------------------------------------
    # 만료
    #
    # ACTIVE → EXPIRED
    # HELD   → AVAILABLE
    # -----------------------------------------------------

    hold.status = "EXPIRED"

    slot.status = "AVAILABLE"


    # commit 아님
    # transaction / row lock 유지
    db.flush()


    return True


# =========================================================
# 실제 Slot HOLD Core Service
#
# FastAPI와 MCP가 모두 이 함수를 사용한다.
# =========================================================

def create_slot_hold(
    db: Session,
    slot_id: int,
    source: str,
    candidate_match_id: int | None = None,
):

    try:

        # =================================================
        # 1. CandidateMatch 확인
        # =================================================

        candidate_match = None


        if candidate_match_id is not None:

            candidate_match = (
                db.query(
                    CandidateMatch
                )
                .filter(
                    CandidateMatch.id
                    == candidate_match_id
                )
                .first()
            )


            if candidate_match is None:

                raise HoldServiceError(
                    status_code=404,
                    detail=(
                        "Candidate match not found"
                    ),
                )


        # =================================================
        # 2. Slot ROW LOCK
        #
        # SELECT ... FOR UPDATE
        # =================================================

        slot = (
            db.query(
                AppointmentSlot
            )
            .filter(
                AppointmentSlot.id
                == slot_id
            )
            .with_for_update()
            .first()
        )


        if slot is None:

            raise HoldServiceError(
                status_code=404,
                detail="Slot not found",
            )


        # =================================================
        # 3. Candidate와 Slot 관계 검증
        # =================================================

        if candidate_match is not None:

            # Candidate Search에서 보여준 슬롯과
            # 실제 HOLD하려는 슬롯이 같은가?
            if (
                candidate_match
                .earliest_slot_id
                != slot.id
            ):

                raise HoldServiceError(
                    status_code=409,
                    detail=(
                        "Candidate does not match "
                        "the requested slot"
                    ),
                )


            # Candidate provider와
            # Slot provider도 같은가?
            if (
                candidate_match
                .provider_id
                != slot.provider_id
            ):

                raise HoldServiceError(
                    status_code=409,
                    detail=(
                        "Candidate provider does not "
                        "match the requested slot"
                    ),
                )


        # =================================================
        # 4. 기존 HOLD 만료 확인
        # =================================================

        release_expired_hold(
            slot=slot,
            db=db,
        )


        # =================================================
        # 5. 실제 AVAILABLE 여부
        # =================================================

        if (
            slot.status
            != "AVAILABLE"
        ):

            raise HoldServiceError(
                status_code=409,
                detail=(
                    "Slot is not available"
                ),
            )


        # =================================================
        # 6. 새 HOLD 만료시간
        # =================================================

        expires_at = (
            datetime.utcnow()
            + timedelta(
                minutes=5
            )
        )


        # =================================================
        # 7. Slot
        #
        # AVAILABLE → HELD
        # =================================================

        slot.status = "HELD"


        # =================================================
        # 8. Hold 생성
        # =================================================

        hold = SlotHold(

            slot_id=
                slot.id,

            source=
                source,

            expires_at=
                expires_at,

            status=
                "ACTIVE",
        )


        db.add(
            hold
        )


        # Hold ID 확보
        # ROW LOCK은 유지
        db.flush()


        # =================================================
        # 9. Transaction Graph
        # =================================================

        if candidate_match is not None:

            # ---------------------------------------------
            # SHOWN → SELECTED
            # ---------------------------------------------

            selected_event = (
                DecisionEvent(

                    intent_id=
                        candidate_match
                        .intent_id,

                    candidate_match_id=
                        candidate_match.id,

                    event_type=
                        "SELECTED",

                    slot_id=
                        slot.id,

                    event_metadata={
                        "source":
                            source,
                    },
                )
            )


            db.add(
                selected_event
            )


            # ---------------------------------------------
            # SELECTED → HELD
            # ---------------------------------------------

            held_event = (
                DecisionEvent(

                    intent_id=
                        candidate_match
                        .intent_id,

                    candidate_match_id=
                        candidate_match.id,

                    event_type=
                        "HELD",

                    slot_id=
                        slot.id,

                    hold_id=
                        hold.id,

                    event_metadata={
                        "source":
                            source,

                        "expires_at":
                            expires_at
                            .isoformat(),
                    },
                )
            )


            db.add(
                held_event
            )


        # =================================================
        # 10. 최종 COMMIT
        #
        # Slot
        # Hold
        # SELECTED
        # HELD
        #
        # 모두 하나의 transaction
        # =================================================

        db.commit()


        return hold


    # =====================================================
    # 우리가 예상한 business error
    # =====================================================

    except HoldServiceError:

        db.rollback()

        raise


    # =====================================================
    # 예상하지 못한 오류
    #
    # transaction을 반드시 정리
    # =====================================================

    except Exception:

        db.rollback()

        raise