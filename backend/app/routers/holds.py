from datetime import (
    datetime,
    timedelta,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models import (
    AppointmentSlot,
    CandidateMatch,
    DecisionEvent,
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
# 기존 직접 HOLD:
#
# POST /slots/2/hold
#
# {
#     "source": "ChatGPT"
# }
#
#
# Candidate Search에서 선택한 HOLD:
#
# POST /slots/2/hold
#
# {
#     "source": "AI_SIMULATOR",
#     "candidate_match_id": 1
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

    # =====================================================
    # 1. CandidateMatch 확인
    #
    # candidate_match_id가 없는 기존 직접 HOLD라면
    # 이 단계는 건너뛴다.
    # =====================================================

    candidate_match = None


    if request.candidate_match_id is not None:

        candidate_match = (
            db.query(CandidateMatch)
            .filter(
                CandidateMatch.id
                == request.candidate_match_id
            )
            .first()
        )


        if candidate_match is None:

            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Candidate match not found",
            )


    # =====================================================
    # 2. 해당 예약 슬롯 찾기 + PostgreSQL ROW LOCK
    #
    # SELECT ... FOR UPDATE
    #
    # 같은 슬롯에 100개 요청이 동시에 들어와도
    # 한 transaction씩 처리된다.
    # =====================================================

    slot = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id
            == slot_id
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
    # 3. Candidate와 Slot이 실제로 연결된 것인지 검증
    #
    # 예:
    #
    # Candidate #1
    # earliest_slot_id = 2
    #
    # 그런데 클라이언트가
    # POST /slots/117/hold
    #
    # 를 보내면 거절한다.
    # =====================================================

    if candidate_match is not None:

        if (
            candidate_match.earliest_slot_id
            != slot.id
        ):

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Candidate does not match "
                    "the requested slot"
                ),
            )


        # -------------------------------------------------
        # Provider도 일치하는지 추가 검증
        # -------------------------------------------------

        if (
            candidate_match.provider_id
            != slot.provider_id
        ):

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Candidate provider does not "
                    "match the requested slot"
                ),
            )


    # =====================================================
    # 4. 기존 HOLD가 만료됐는지 확인
    #
    # 만료됐다면:
    #
    # ACTIVE → EXPIRED
    # HELD   → AVAILABLE
    #
    # 아직 COMMIT하지 않으므로
    # ROW LOCK은 계속 유지된다.
    # =====================================================

    release_expired_hold(
        slot=slot,
        db=db,
    )


    # =====================================================
    # 5. AVAILABLE 상태 확인
    #
    # 다른 사용자가 먼저 HOLD했다면
    # 여기서 409
    # =====================================================

    if slot.status != "AVAILABLE":

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Slot is not available",
        )


    # =====================================================
    # 6. 새 HOLD 만료시간
    # =====================================================

    expires_at = (
        datetime.utcnow()
        + timedelta(minutes=5)
    )


    # =====================================================
    # 7. Slot 상태 변경
    #
    # AVAILABLE → HELD
    # =====================================================

    slot.status = "HELD"


    # =====================================================
    # 8. SlotHold 생성
    # =====================================================

    hold = SlotHold(

        slot_id=
            slot.id,

        source=
            request.source,

        expires_at=
            expires_at,

        status=
            "ACTIVE",
    )


    db.add(
        hold
    )


    # -----------------------------------------------------
    # hold.id가 필요하므로
    # COMMIT 전에 INSERT를 DB에 전달
    #
    # transaction은 아직 끝나지 않음
    # ROW LOCK도 유지
    # -----------------------------------------------------

    db.flush()


    # =====================================================
    # 9. Transaction Graph 기록
    #
    # Candidate Search에서 시작된 HOLD인 경우만
    # SELECTED / HELD event 생성
    # =====================================================

    if candidate_match is not None:

        # -------------------------------------------------
        # 사용자가 이 후보를 선택했다.
        #
        # SHOWN
        #   ↓
        # SELECTED
        # -------------------------------------------------

        selected_event = DecisionEvent(

            intent_id=
                candidate_match.intent_id,

            candidate_match_id=
                candidate_match.id,

            event_type=
                "SELECTED",

            slot_id=
                slot.id,

            event_metadata={
                "source":
                    request.source,
            },
        )


        db.add(
            selected_event
        )


        # -------------------------------------------------
        # 실제 슬롯 HOLD 성공
        #
        # SELECTED
        #   ↓
        # HELD
        # -------------------------------------------------

        held_event = DecisionEvent(

            intent_id=
                candidate_match.intent_id,

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
                    request.source,

                "expires_at":
                    expires_at.isoformat(),
            },
        )


        db.add(
            held_event
        )


    # =====================================================
    # 10. 최종 COMMIT
    #
    # 아래 변경이 한 transaction으로 확정된다.
    #
    # Slot:
    # AVAILABLE → HELD
    #
    # SlotHold:
    # ACTIVE 생성
    #
    # DecisionEvent:
    # SELECTED
    # HELD
    #
    # COMMIT 후 ROW LOCK 해제
    # =====================================================

    db.commit()


    # expire_on_commit=False이므로
    # 다시 db.refresh()할 필요 없음

    return hold