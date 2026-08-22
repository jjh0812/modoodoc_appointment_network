from sqlalchemy.exc import (
    IntegrityError,
)

from sqlalchemy.orm import Session

from app.models import (
    CandidateMatch,
    DecisionEvent,
    PatientIntent,
)

from app.models_decision_feedback import (
    DecisionFeedback,
)


# =========================================================
# Service Error
# =========================================================

class DecisionFeedbackError(
    Exception
):

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
# 기존 Idempotency Feedback 확인
# =========================================================

def find_existing_feedback(
    db: Session,
    idempotency_key: str,
):

    return (
        db.query(
            DecisionFeedback
        )
        .filter(
            DecisionFeedback
            .idempotency_key
            == idempotency_key
        )
        .first()
    )


# =========================================================
# 1. 선택 이유 저장
#
# 반드시:
#
# Candidate가 해당 Intent 소속
# +
# 실제 SELECTED Event가 존재
#
# 해야 저장 가능
# =========================================================

def create_selection_feedback(
    db: Session,
    intent_id: int,
    candidate_match_id: int,
    reason_codes: list[str],
    free_text: str | None,
    source: str,
    idempotency_key: str,
):

    try:

        # =================================================
        # 1. Idempotency
        # =================================================

        existing = (
            find_existing_feedback(
                db=db,
                idempotency_key=
                    idempotency_key,
            )
        )


        if existing is not None:

            return existing


        # =================================================
        # 2. Intent 확인
        # =================================================

        intent = (
            db.query(
                PatientIntent
            )
            .filter(
                PatientIntent.id
                == intent_id
            )
            .first()
        )


        if intent is None:

            raise DecisionFeedbackError(
                status_code=404,
                detail="Patient intent not found",
            )


        # =================================================
        # 3. Candidate 확인
        # =================================================

        candidate = (
            db.query(
                CandidateMatch
            )
            .filter(
                CandidateMatch.id
                == candidate_match_id
            )
            .first()
        )


        if candidate is None:

            raise DecisionFeedbackError(
                status_code=404,
                detail="Candidate match not found",
            )


        # =================================================
        # 4. Candidate가 이 Intent 소속인가
        # =================================================

        if (
            candidate.intent_id
            != intent_id
        ):

            raise DecisionFeedbackError(
                status_code=409,
                detail=(
                    "Candidate does not belong "
                    "to the requested intent"
                ),
            )


        # =================================================
        # 5. 실제 SELECTED Event가 있었는가
        #
        # 아무 후보나 골라놓고
        # "선택 이유"를 기록할 수 없게 한다.
        # =================================================

        selected_event = (
            db.query(
                DecisionEvent
            )
            .filter(
                DecisionEvent.intent_id
                == intent_id,

                DecisionEvent
                .candidate_match_id
                == candidate_match_id,

                DecisionEvent.event_type
                == "SELECTED",
            )
            .order_by(
                DecisionEvent.id.desc()
            )
            .first()
        )


        if selected_event is None:

            raise DecisionFeedbackError(
                status_code=409,
                detail=(
                    "Selection feedback requires "
                    "a SELECTED decision event"
                ),
            )


        # =================================================
        # 6. Feedback 생성
        # =================================================

        feedback = DecisionFeedback(

            intent_id=
                intent_id,

            candidate_match_id=
                candidate_match_id,

            feedback_type=
                "SELECTION_REASON",

            reason_codes=
                reason_codes,

            free_text=
                free_text,

            source=
                source,

            idempotency_key=
                idempotency_key,
        )


        db.add(
            feedback
        )


        db.commit()


        return feedback


    except DecisionFeedbackError:

        db.rollback()

        raise


    except IntegrityError:

        db.rollback()


        existing = (
            find_existing_feedback(
                db=db,
                idempotency_key=
                    idempotency_key,
            )
        )


        if existing is not None:

            return existing


        raise


    except Exception:

        db.rollback()

        raise


# =========================================================
# 2. 아무 후보도 선택하지 않은 이유
#
# 반드시:
#
# Intent 존재
# +
# 해당 Intent에 SELECTED가 없음
#
# 이어야 한다.
# =========================================================

def create_no_selection_feedback(
    db: Session,
    intent_id: int,
    reason_codes: list[str],
    free_text: str | None,
    source: str,
    idempotency_key: str,
):

    try:

        # =================================================
        # 1. Idempotency
        # =================================================

        existing = (
            find_existing_feedback(
                db=db,
                idempotency_key=
                    idempotency_key,
            )
        )


        if existing is not None:

            return existing


        # =================================================
        # 2. Intent
        # =================================================

        intent = (
            db.query(
                PatientIntent
            )
            .filter(
                PatientIntent.id
                == intent_id
            )
            .first()
        )


        if intent is None:

            raise DecisionFeedbackError(
                status_code=404,
                detail="Patient intent not found",
            )


        # =================================================
        # 3. 이미 SELECTED가 있으면
        #    NO_SELECTION이라고 기록하면 안 됨
        # =================================================

        selected_event = (
            db.query(
                DecisionEvent
            )
            .filter(
                DecisionEvent.intent_id
                == intent_id,

                DecisionEvent.event_type
                == "SELECTED",
            )
            .first()
        )


        if selected_event is not None:

            raise DecisionFeedbackError(
                status_code=409,
                detail=(
                    "No-selection feedback "
                    "cannot be recorded after "
                    "a candidate was selected"
                ),
            )


        # =================================================
        # 4. Feedback
        # =================================================

        feedback = DecisionFeedback(

            intent_id=
                intent_id,

            candidate_match_id=
                None,

            feedback_type=
                "NO_SELECTION_REASON",

            reason_codes=
                reason_codes,

            free_text=
                free_text,

            source=
                source,

            idempotency_key=
                idempotency_key,
        )


        db.add(
            feedback
        )


        db.commit()


        return feedback


    except DecisionFeedbackError:

        db.rollback()

        raise


    except IntegrityError:

        db.rollback()


        existing = (
            find_existing_feedback(
                db=db,
                idempotency_key=
                    idempotency_key,
            )
        )


        if existing is not None:

            return existing


        raise


    except Exception:

        db.rollback()

        raise