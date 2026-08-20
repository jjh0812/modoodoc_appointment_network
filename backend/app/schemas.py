from datetime import (
    date,
    datetime,
)

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# 1. AppointmentSlot API 응답 형태
# =========================================================

class AppointmentSlotResponse(BaseModel):

    id: int

    provider_id: int

    start_time: datetime

    status: str


    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# 2. Slot Hold 요청
#
# 기존:
#
# {
#     "source": "ChatGPT"
# }
#
# 새 방식:
#
# {
#     "source": "ChatGPT",
#     "candidate_match_id": 1
# }
#
# candidate_match_id를 함께 보내면
# 어떤 검색 후보를 사용자가 선택해서 HOLD했는지
# Transaction Graph에 연결할 수 있다.
# =========================================================

class SlotHoldRequest(BaseModel):

    # -----------------------------------------------------
    # HOLD 요청 출처
    #
    # 예:
    # ChatGPT
    # AI_SIMULATOR
    # CHATGPT_MCP
    # WEB
    # -----------------------------------------------------

    source: str


    # -----------------------------------------------------
    # Constraint Match에서 생성된 CandidateMatch ID
    #
    # 예:
    #
    # PatientIntent #3
    #       ↓
    # CandidateMatch #1
    #       ↓
    # 사용자가 후보 #1 선택
    #       ↓
    # candidate_match_id = 1
    #       ↓
    # HOLD
    #
    #
    # nullable인 이유:
    #
    # 기존 직접 슬롯 HOLD 방식도 계속 지원하기 위해서.
    #
    # 기존 concurrency test:
    #
    # {
    #     "source": "concurrency-test-9"
    # }
    #
    # 도 그대로 작동해야 한다.
    # -----------------------------------------------------

    candidate_match_id: int | None = None


# =========================================================
# 3. Slot Hold 응답
#
# HOLD 성공 후 외부 AI에게 돌려줄 정보
# =========================================================

class SlotHoldResponse(BaseModel):

    id: int

    slot_id: int

    source: str

    expires_at: datetime

    status: str


    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# 4. 예약 확정 요청
# =========================================================

class AppointmentConfirmRequest(BaseModel):

    # -----------------------------------------------------
    # 같은 요청이 여러 번 들어와도
    # 예약을 하나만 생성하기 위한 고유 키
    #
    # 예:
    # booking-chatgpt-001
    # -----------------------------------------------------

    idempotency_key: str


# =========================================================
# 5. 예약 확정 결과
# =========================================================

class AppointmentResponse(BaseModel):

    # 실제 예약 번호
    id: int

    # 어떤 예약 슬롯인지
    slot_id: int

    # 어떤 HOLD를 확정한 것인지
    hold_id: int

    # 요청 출처
    source: str

    # 중복 요청 방지 키
    idempotency_key: str

    # 예약 상태
    status: str

    # 예약 생성 시각
    created_at: datetime


    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# 6. Care Option Search 요청
#
# 현재 단계에서는 자연어를 직접 해석하지 않는다.
#
# 이미 구조화된 Patient Intent를 받아서:
#
# Canonical Offer
# +
# Hospital
# +
# Provider
# +
# Availability
#
# 를 검색한다.
# =========================================================

class CareOptionsSearchRequest(BaseModel):

    # -----------------------------------------------------
    # 모두닥 canonical procedure
    #
    # 예:
    # VISION_CORRECTION_SMILE
    # -----------------------------------------------------

    procedure_code: str


    # -----------------------------------------------------
    # 지역
    #
    # 사용자는:
    #
    # 강남
    # 강남역
    # 역삼
    #
    # 등으로 입력할 수 있다.
    #
    # 이후 Intent Normalization Layer에서
    # 강남구로 정규화된다.
    # -----------------------------------------------------

    district: str | None = None


    # -----------------------------------------------------
    # 원하는 날짜
    #
    # 예:
    # 2026-08-22
    # -----------------------------------------------------

    preferred_date: date


    # -----------------------------------------------------
    # 원하는 시간대
    # -----------------------------------------------------

    time_window: Literal[
        "MORNING",
        "AFTERNOON",
        "EVENING",
        "ANY",
    ] = "ANY"


    # -----------------------------------------------------
    # 최대 예산
    #
    # 원 단위
    #
    # 예:
    # 2,000,000
    # -----------------------------------------------------

    budget_max: int | None = None


    # -----------------------------------------------------
    # Intent가 어디서 들어왔는가
    #
    # 예:
    # AI_SIMULATOR
    # CHATGPT_MCP
    # WEB
    # -----------------------------------------------------

    source: str = "AI_SIMULATOR"


    # -----------------------------------------------------
    # 사용자가 실제 입력한 원문
    #
    # 예:
    #
    # "8월 22일 오후 강남에서
    #  200만원 정도로 스마일 시력교정
    #  검진 가능한 곳 찾아줘"
    #
    # Canonical Intent와 별도로 원문을 보존한다.
    # -----------------------------------------------------

    raw_query: str | None = None


    # -----------------------------------------------------
    # 최대 몇 개 후보를 반환할 것인가
    #
    # 기본 = 3
    # 최소 = 1
    # 최대 = 10
    # -----------------------------------------------------

    limit: int = Field(
        default=3,
        ge=1,
        le=10,
    )


# =========================================================
# 7. 검색된 Care Option 후보 하나
#
# 주의:
#
# constraint_match_score는
# 의료적 품질 점수가 아니다.
#
# 사용자의 명시적 조건과 얼마나 일치하는지
# 나타내는 matching score다.
# =========================================================

class CareOptionCandidateResponse(BaseModel):

    # -----------------------------------------------------
    # CandidateMatch DB ID
    #
    # 이 ID가 이후:
    #
    # SELECTED
    # → HELD
    # → CONFIRMED
    #
    # 흐름을 연결하는 핵심 ID가 된다.
    # -----------------------------------------------------

    candidate_match_id: int


    # -----------------------------------------------------
    # Provider
    # -----------------------------------------------------

    provider_id: int

    provider_name: str


    # -----------------------------------------------------
    # Hospital
    # -----------------------------------------------------

    hospital_id: int

    hospital_name: str

    district: str


    # -----------------------------------------------------
    # Canonical ProviderOffer
    # -----------------------------------------------------

    offer_id: int

    procedure_code: str

    procedure_name: str


    # -----------------------------------------------------
    # 가격
    # -----------------------------------------------------

    price_min: int | None

    price_max: int | None


    # -----------------------------------------------------
    # 가장 빠른 실제 AVAILABLE slot
    # -----------------------------------------------------

    earliest_slot_id: int

    earliest_slot_time: datetime


    # -----------------------------------------------------
    # Constraint Matching
    #
    # 의료 품질 점수가 아니라
    # 사용자 조건 일치 점수
    # -----------------------------------------------------

    constraint_match_score: float

    budget_status: str


    # -----------------------------------------------------
    # 이 Offer normalization 자체의 confidence
    #
    # 예:
    # 0.99
    #
    # 이것 역시 의사 품질 점수가 아니다.
    #
    # 병원 RAW 데이터를 우리가 얼마나 확실하게
    # canonical ProviderOffer로 정규화했는지에 대한 점수.
    # -----------------------------------------------------

    data_confidence: float


    # -----------------------------------------------------
    # 왜 이 후보가 검색됐는지
    #
    # 예:
    #
    # 강남구 지역 조건 일치
    # 예상가격 예산 이내
    # 14:20 예약 가능
    # 정규화 데이터 신뢰도 0.99
    # -----------------------------------------------------

    reasons: list[str]


# =========================================================
# 8. Care Option Search 전체 응답
# =========================================================

class CareOptionsSearchResponse(BaseModel):

    # -----------------------------------------------------
    # 이번 검색에서 생성된 PatientIntent ID
    # -----------------------------------------------------

    intent_id: int


    # -----------------------------------------------------
    # 실제 사용자에게 보여준 후보
    # -----------------------------------------------------

    candidates: list[
        CareOptionCandidateResponse
    ]