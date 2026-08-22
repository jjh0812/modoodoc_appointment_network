from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.database import (
    get_db,
)

from app.services.decision_analytics_service import (
    get_decision_funnel,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


# =========================================================
# GET /analytics/decision-funnel
# =========================================================

@router.get(
    "/decision-funnel"
)
def decision_funnel(
    db: Session = Depends(
        get_db
    ),
):

    return get_decision_funnel(
        db=db
    )