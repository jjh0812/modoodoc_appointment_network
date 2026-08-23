from fastapi import (
    APIRouter,
    Response,
    status,
)

from sqlalchemy import text

from sqlalchemy.exc import (
    SQLAlchemyError,
)

from app.database import (
    engine,
)


# =========================================================
# Health Router
# =========================================================

router = APIRouter(
    prefix="/health",
    tags=[
        "health",
    ],
)


# =========================================================
# 1. Liveness
#
# GET /health/live
#
# 의미:
#
# FastAPI 프로세스가 요청을 받을 수 있는가?
#
# DB 상태는 확인하지 않는다.
#
# 서버 프로세스 자체가 살아 있으면 200 OK.
# =========================================================

@router.get(
    "/live"
)
def health_live():

    return {

        "status":
            "ok",

        "service":
            "modoodoc-appointment-network",
    }


# =========================================================
# 2. Readiness
#
# GET /health/ready
#
# 의미:
#
# 이 서버가 실제 요청을 처리할 준비가 되었는가?
#
# PostgreSQL에 SELECT 1을 보내
# DB 연결 가능 여부까지 확인한다.
#
#
# 정상:
#
# HTTP 200
#
# {
#     "status": "ready",
#     "database": "ok"
# }
#
#
# DB 장애:
#
# HTTP 503
#
# {
#     "status": "not_ready",
#     "database": "unavailable"
# }
#
#
# 실제 DB 비밀번호나 내부 에러 메시지는
# 외부 응답에 노출하지 않는다.
# =========================================================

@router.get(
    "/ready"
)
def health_ready(
    response: Response,
):

    try:

        with engine.connect() as connection:

            connection.execute(
                text(
                    "SELECT 1"
                )
            )


    except SQLAlchemyError:

        response.status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
        )


        return {

            "status":
                "not_ready",

            "database":
                "unavailable",
        }


    return {

        "status":
            "ready",

        "database":
            "ok",
    }