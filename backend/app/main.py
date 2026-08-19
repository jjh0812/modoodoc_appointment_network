from fastapi import FastAPI

from app.database import Base, engine

from app.routers.availability import (
    router as availability_router,
)

from app.routers.holds import (
    router as holds_router,
)

from app.routers.appointments import (
    router as appointments_router,
)


# =========================================================
# 1. DB 테이블 생성
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# 2. FastAPI 앱 생성
# =========================================================

app = FastAPI(
    title="Modoodoc Appointment Network Prototype"
)


# =========================================================
# 3. Availability API 연결
#
# GET /providers/{provider_id}/availability
# =========================================================

app.include_router(
    availability_router
)


# =========================================================
# 4. HOLD API 연결
#
# POST /slots/{slot_id}/hold
# =========================================================

app.include_router(
    holds_router
)


# =========================================================
# 5. Appointment API 연결
#
# POST /holds/{hold_id}/confirm
# =========================================================

app.include_router(
    appointments_router
)


# =========================================================
# 6. 서버 정상 작동 확인용 API
# =========================================================

@app.get("/")
def health_check():

    return {
        "service": "modoodoc-appointment-network",
        "status": "ok",
    }