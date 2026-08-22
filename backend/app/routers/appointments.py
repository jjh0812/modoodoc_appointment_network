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
    AppointmentConfirmRequest,
    AppointmentResponse,
)

from app.services.appointment_service import (
    AppointmentServiceError,
    confirm_slot_hold,
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
# Router는 HTTP 입출력만 담당한다.
#
# 실제 business logic:
#
# appointment_service.py
#     ↓
# confirm_slot_hold()
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

    try:

        return confirm_slot_hold(

            db=db,

            hold_id=
                hold_id,

            idempotency_key=
                request.idempotency_key,
        )


    except AppointmentServiceError as error:

        raise HTTPException(

            status_code=
                error.status_code,

            detail=
                error.detail,
        )