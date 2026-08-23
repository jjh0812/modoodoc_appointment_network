from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.database import (
    Base,
    engine,
)

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

from app.routers.analytics import (
    router as analytics_router,
)

from app.routers.decision_feedback import (
    router as decision_feedback_router,
)

from app.routers.health import (
    router as health_router,
)

from app.request_context import (
    RequestContextMiddleware,
)


# =========================================================
# 1. DB 테이블 생성
#
# 각 Router / Service가 import되면서
# SQLAlchemy Model들이 Base.metadata에 등록된다.
#
# 그 다음 create_all()이:
#
# 기존 테이블은 유지
# +
# 새 테이블이 없으면 생성
#
# 한다.
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# 2. FastAPI 앱 생성
# =========================================================

app = FastAPI(
    title=(
        "Modoodoc Appointment "
        "Network Prototype"
    )
)


# =========================================================
# 3. Request Context Middleware
#
# 모든 HTTP 요청에:
#
# 1. X-Request-ID 생성 또는 전달
# 2. 요청 처리 시간 측정
# 3. Structured JSON Log 기록
# 4. Response Header에 X-Request-ID 반환
#
# 을 수행한다.
# =========================================================

app.add_middleware(
    RequestContextMiddleware
)


# =========================================================
# 4. CORS 설정
#
# Next.js:
# localhost:3000
#
# FastAPI:
# localhost:8001
#
# 브라우저가 서로 통신할 수 있도록 허용한다.
#
#
# X-Request-ID:
#
# Backend가 반환한 Request ID를
# Frontend JavaScript에서도 읽을 수 있도록
# expose_headers에 추가한다.
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

    expose_headers=[
        "X-Request-ID",
    ],
)


# =========================================================
# 5. Availability API
#
# GET /providers/{provider_id}/availability
# =========================================================

app.include_router(
    availability_router
)


# =========================================================
# 6. HOLD API
#
# POST /slots/{slot_id}/hold
#
# AVAILABLE
#     ↓
# SELECTED
#     ↓
# HELD
# =========================================================

app.include_router(
    holds_router
)


# =========================================================
# 7. Appointment API
#
# POST /holds/{hold_id}/confirm
#
# HELD
#     ↓
# CONFIRMED
# =========================================================

app.include_router(
    appointments_router
)


# =========================================================
# 8. Care Options API
#
# POST /care-options/search
#
# Patient Intent
#     ↓
# Intent Normalization
#     ↓
# Canonical ProviderOffer
#     +
# Availability
#     ↓
# Constraint Match
#     ↓
# Top Candidates
#     ↓
# SHOWN
# =========================================================

app.include_router(
    care_options_router
)


# =========================================================
# 9. Decision Analytics API
#
# GET /analytics/decision-funnel
#
# GET /analytics/hospitals
#
# GET
# /analytics/hospitals/{hospital_id}/decision-loss
#
#
# 분석 대상:
#
# SEARCHED
#     ↓
# SHOWN
#     ↓
# SELECTED
#     ↓
# HELD
#     ↓
# CONFIRMED
#
#
# 그리고 병원별:
#
# 노출
# 선택
# 예약
# Loss Signal
#
# 을 분석한다.
# =========================================================

app.include_router(
    analytics_router
)


# =========================================================
# 10. Decision Feedback API
#
# 사용자가 직접 밝힌
# "선택 이유 / 비선택 이유" 저장
#
#
# POST /decision-feedback/selection
#
# 예:
#
# PRICE
# AVAILABILITY
# LOCATION
# DATA_CONFIDENCE
#
#
# POST /decision-feedback/no-selection
#
# 예:
#
# BUDGET_TOO_HIGH
# TIME_NOT_MATCH
# LOCATION_NOT_MATCH
# INSUFFICIENT_INFORMATION
#
#
# DecisionEvent:
# "사용자가 무엇을 했는가"
#
# DecisionFeedback:
# "사용자가 왜 그렇게 했다고 말했는가"
# =========================================================

app.include_router(
    decision_feedback_router
)


# =========================================================
# 11. Operational Health API
#
# GET /health/live
#
# FastAPI 프로세스가
# 요청을 받을 수 있는지 확인한다.
#
#
# GET /health/ready
#
# PostgreSQL까지 실제 연결 가능한지 확인한다.
#
# 정상:
# HTTP 200
#
# DB 연결 불가:
# HTTP 503
# =========================================================

app.include_router(
    health_router
)


# =========================================================
# 12. Legacy Root Health Check
#
# GET /
#
# 기존 regression_suite.py와
# 호환성을 유지하기 위해 그대로 둔다.
# =========================================================

@app.get("/")
def health_check():

    return {

        "service":
            "modoodoc-appointment-network",

        "status":
            "ok",
    }