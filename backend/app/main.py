from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

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

from app.routers.care_options import (
    router as care_options_router,
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
# 3. CORS 설정
#
# Next.js:
# localhost:3000
#
# FastAPI:
# localhost:8001
#
# 브라우저가 서로 통신할 수 있도록 허용
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],

    allow_credentials=True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# =========================================================
# 4. Availability API 연결
#
# GET /providers/{provider_id}/availability
# =========================================================

app.include_router(
    availability_router
)


# =========================================================
# 5. HOLD API 연결
#
# POST /slots/{slot_id}/hold
# =========================================================

app.include_router(
    holds_router
)


# =========================================================
# 6. Appointment API 연결
#
# POST /holds/{hold_id}/confirm
# =========================================================

app.include_router(
    appointments_router
)


# =========================================================
# 7. Care Options API 연결
#
# POST /care-options/search
#
# Patient Intent
#     ↓
# Canonical ProviderOffer
#     ↓
# Availability
#     ↓
# Constraint Match
#     ↓
# Top Candidates
# =========================================================

app.include_router(
    care_options_router
)


# =========================================================
# 8. 서버 정상 작동 확인용 API
# =========================================================

@app.get("/")
def health_check():

    return {
        "service": "modoodoc-appointment-network",
        "status": "ok",
    }