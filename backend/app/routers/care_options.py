from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.schemas import (
    CareOptionsSearchRequest,
    CareOptionsSearchResponse,
)

from app.services.care_option_match_service import (
    search_care_options,
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/care-options",
    tags=["care-options"],
)


# =========================================================
# Constraint Match Search
#
# POST /care-options/search
# =========================================================

@router.post(
    "/search",
    response_model=CareOptionsSearchResponse,
)
def search(
    request: CareOptionsSearchRequest,
    db: Session = Depends(get_db),
):

    try:

        return search_care_options(

            db=db,

            procedure_code=
                request.procedure_code,

            district=
                request.district,

            preferred_date=
                request.preferred_date,

            time_window=
                request.time_window,

            budget_max=
                request.budget_max,

            source=
                request.source,

            raw_query=
                request.raw_query,

            limit=
                request.limit,
        )


    except ValueError as error:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )