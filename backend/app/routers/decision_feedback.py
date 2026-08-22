from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import (
    get_db,
)

from app.decision_feedback_schemas import (
    DecisionFeedbackResponse,
    NoSelectionFeedbackRequest,
    SelectionFeedbackRequest,
)

from app.services.decision_feedback_service import (
    DecisionFeedbackError,
    create_no_selection_feedback,
    create_selection_feedback,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/decision-feedback",
    tags=["decision-feedback"],
)


# =========================================================
# 1. 선택 이유
#
# POST /decision-feedback/selection
# =========================================================

@router.post(
    "/selection",
    response_model=
        DecisionFeedbackResponse,
)
def selection_feedback(
    request:
        SelectionFeedbackRequest,

    db: Session = Depends(
        get_db
    ),
):

    try:

        return create_selection_feedback(

            db=db,

            intent_id=
                request.intent_id,

            candidate_match_id=
                request.candidate_match_id,

            reason_codes=
                list(
                    request.reason_codes
                ),

            free_text=
                request.free_text,

            source=
                request.source,

            idempotency_key=
                request.idempotency_key,
        )


    except DecisionFeedbackError as error:

        raise HTTPException(
            status_code=
                error.status_code,

            detail=
                error.detail,
        )


# =========================================================
# 2. 아무 후보도 선택하지 않은 이유
#
# POST /decision-feedback/no-selection
# =========================================================

@router.post(
    "/no-selection",
    response_model=
        DecisionFeedbackResponse,
)
def no_selection_feedback(
    request:
        NoSelectionFeedbackRequest,

    db: Session = Depends(
        get_db
    ),
):

    try:

        return create_no_selection_feedback(

            db=db,

            intent_id=
                request.intent_id,

            reason_codes=
                list(
                    request.reason_codes
                ),

            free_text=
                request.free_text,

            source=
                request.source,

            idempotency_key=
                request.idempotency_key,
        )


    except DecisionFeedbackError as error:

        raise HTTPException(
            status_code=
                error.status_code,

            detail=
                error.detail,
        )