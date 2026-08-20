from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from app.database import Base


# =========================================================
# 1. Hospital
#
# 병원 자체
#
# 예:
# 강남비전안과
# 서울아이안과
# =========================================================

class Hospital(Base):

    __tablename__ = "hospitals"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    name = Column(
        String,
        nullable=False,
    )


    # 예:
    # 서울
    region = Column(
        String,
        nullable=False,
    )


    # 예:
    # 강남구
    district = Column(
        String,
        nullable=False,
    )


    # 실제 주소 대신
    # prototype용 간단한 위치 문자열
    address_label = Column(
        String,
        nullable=True,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    providers = relationship(
        "Provider",
        back_populates="hospital",
    )


    raw_offer_evidence = relationship(
        "RawOfferEvidence",
        back_populates="hospital",
    )


# =========================================================
# 2. Provider
#
# 병원 안에서 실제 진료하는 의사
# =========================================================

class Provider(Base):

    __tablename__ = "providers"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    # -----------------------------------------------------
    # 어느 병원 소속인지
    # -----------------------------------------------------

    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id"),
        nullable=False,
    )


    name = Column(
        String,
        nullable=False,
    )


    specialty = Column(
        String,
        nullable=False,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    hospital = relationship(
        "Hospital",
        back_populates="providers",
    )


    slots = relationship(
        "AppointmentSlot",
        back_populates="provider",
    )


    offers = relationship(
        "ProviderOffer",
        back_populates="provider",
    )


    raw_offer_evidence = relationship(
        "RawOfferEvidence",
        back_populates="provider",
    )


# =========================================================
# 3. RawOfferEvidence
#
# 병원이 실제로 보내거나,
# 홈페이지 / CSV / API 등에서 받은 원본 데이터
#
# 중요:
# 이 데이터는 정규화하기 전에 그대로 보존한다.
# =========================================================

class RawOfferEvidence(Base):

    __tablename__ = "raw_offer_evidence"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id"),
        nullable=False,
    )


    # 원본 데이터가 특정 의사를 명시하지 않는 경우도
    # 있기 때문에 nullable=True
    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=True,
    )


    # -----------------------------------------------------
    # 원본 데이터가 어디서 왔는지
    #
    # 예:
    #
    # JSON_API
    # CSV
    # ADMIN
    # FREE_TEXT
    # WEBSITE
    # FHIR
    # -----------------------------------------------------

    source_type = Column(
        String,
        nullable=False,
    )


    # -----------------------------------------------------
    # 원본 출처 설명
    #
    # 예:
    # hospital_admin
    # price_2026_08.csv
    # /api/offers
    # -----------------------------------------------------

    source_reference = Column(
        String,
        nullable=True,
    )


    # -----------------------------------------------------
    # 원본 자체
    #
    # JSON이든 CSV 한 줄이든 자유 텍스트든
    # 일단 문자열 형태로 그대로 보존
    # -----------------------------------------------------

    raw_payload = Column(
        Text,
        nullable=False,
    )


    # -----------------------------------------------------
    # 원본 내용의 SHA-256
    #
    # 나중에:
    # "같은 데이터 또 들어왔나?"
    # "원본이 바뀌었나?"
    #
    # 확인하는 데 사용
    # -----------------------------------------------------

    content_hash = Column(
        String,
        nullable=False,
        index=True,
    )


    # -----------------------------------------------------
    # 실제 데이터가 관찰된 시각
    #
    # 병원이 "8월 20일 기준 가격"이라고 했다면
    # 그 기준 시각
    # -----------------------------------------------------

    observed_at = Column(
        DateTime,
        nullable=True,
    )


    # -----------------------------------------------------
    # 모두닥이 이 데이터를 받은 시각
    # -----------------------------------------------------

    received_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    # -----------------------------------------------------
    # 정규화 처리 상태
    #
    # RECEIVED
    # NORMALIZED
    # REVIEW_REQUIRED
    # REJECTED
    # -----------------------------------------------------

    normalization_status = Column(
        String,
        nullable=False,
        default="RECEIVED",
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    hospital = relationship(
        "Hospital",
        back_populates="raw_offer_evidence",
    )


    provider = relationship(
        "Provider",
        back_populates="raw_offer_evidence",
    )


    normalized_offers = relationship(
        "ProviderOffer",
        back_populates="raw_evidence",
    )


# =========================================================
# 4. ProviderOffer
#
# 뒤죽박죽 Raw 데이터를
# 모두닥 표준 형태로 변환한 결과
#
# Constraint Match / AI는
# Raw 데이터가 아니라 이 테이블을 사용한다.
# =========================================================

class ProviderOffer(Base):

    __tablename__ = "provider_offers"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
    )


    # -----------------------------------------------------
    # 이 표준 Offer가
    # 어떤 원본 evidence에서 만들어졌는지
    # -----------------------------------------------------

    raw_evidence_id = Column(
        Integer,
        ForeignKey("raw_offer_evidence.id"),
        nullable=True,
    )


    # -----------------------------------------------------
    # 모두닥 내부 표준 시술 코드
    #
    # 예:
    # VISION_CORRECTION_SMILE
    # VISION_CORRECTION_LASIK
    # VISION_CORRECTION_LASEK
    # -----------------------------------------------------

    procedure_code = Column(
        String,
        nullable=False,
        index=True,
    )


    # 사람이 읽는 이름
    procedure_name = Column(
        String,
        nullable=False,
    )


    # -----------------------------------------------------
    # 예상 가격 범위
    #
    # 원 단위
    # -----------------------------------------------------

    price_min = Column(
        Integer,
        nullable=True,
    )


    price_max = Column(
        Integer,
        nullable=True,
    )


    currency = Column(
        String,
        nullable=False,
        default="KRW",
    )


    # -----------------------------------------------------
    # 검사비가 가격에 포함됐는지
    #
    # 원본에서 판단 불가능할 수도 있으므로
    # nullable=True
    # -----------------------------------------------------

    inspection_fee_included = Column(
        Boolean,
        nullable=True,
    )


    # -----------------------------------------------------
    # 특정 조건에 따라 가격이 달라지는 offer인지
    #
    # 예:
    # 당일 수술 시 할인
    # 특정 검사 포함 시 가격 변경
    # -----------------------------------------------------

    conditional_discount = Column(
        Boolean,
        nullable=False,
        default=False,
    )


    # -----------------------------------------------------
    # 실제 예약 가능한 offer인지
    # -----------------------------------------------------

    bookable = Column(
        Boolean,
        nullable=False,
        default=True,
    )


    # -----------------------------------------------------
    # Normalizer의 신뢰도
    #
    # 0.0 ~ 1.0
    #
    # 예:
    # 0.98 = 매우 확실
    # 0.61 = 사람 검토 필요 가능성
    # -----------------------------------------------------

    confidence = Column(
        Float,
        nullable=False,
        default=1.0,
    )


    # -----------------------------------------------------
    # 정규화 결과 상태
    #
    # VERIFIED
    # AUTO_NORMALIZED
    # REVIEW_REQUIRED
    # STALE
    # -----------------------------------------------------

    normalization_status = Column(
        String,
        nullable=False,
        default="AUTO_NORMALIZED",
    )


    # -----------------------------------------------------
    # 언제 이 canonical offer를 확인했는지
    # -----------------------------------------------------

    verified_at = Column(
        DateTime,
        nullable=True,
    )


    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    provider = relationship(
        "Provider",
        back_populates="offers",
    )


    raw_evidence = relationship(
        "RawOfferEvidence",
        back_populates="normalized_offers",
    )


# =========================================================
# 5. AppointmentSlot
#
# 실제 예약 가능한 시간
# =========================================================

class AppointmentSlot(Base):

    __tablename__ = "appointment_slots"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
    )


    start_time = Column(
        DateTime,
        nullable=False,
    )


    status = Column(
        String,
        nullable=False,
        default="AVAILABLE",
    )


    provider = relationship(
        "Provider",
        back_populates="slots",
    )


# =========================================================
# 6. SlotHold
#
# 예약 슬롯을 일정 시간 임시로 잠금
# =========================================================

class SlotHold(Base):

    __tablename__ = "slot_holds"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    slot_id = Column(
        Integer,
        ForeignKey("appointment_slots.id"),
        nullable=False,
    )


    source = Column(
        String,
        nullable=False,
    )


    expires_at = Column(
        DateTime,
        nullable=False,
    )


    status = Column(
        String,
        nullable=False,
        default="ACTIVE",
    )


    slot = relationship(
        "AppointmentSlot"
    )


# =========================================================
# 7. Appointment
#
# 실제 확정 예약
# =========================================================

class Appointment(Base):

    __tablename__ = "appointments"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    # 한 슬롯에는 확정 예약 하나
    slot_id = Column(
        Integer,
        ForeignKey("appointment_slots.id"),
        nullable=False,
        unique=True,
    )


    # 같은 HOLD를 두 번 확정할 수 없음
    hold_id = Column(
        Integer,
        ForeignKey("slot_holds.id"),
        nullable=False,
        unique=True,
    )


    source = Column(
        String,
        nullable=False,
    )


    # 같은 transaction retry 방지
    idempotency_key = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )


    status = Column(
        String,
        nullable=False,
        default="CONFIRMED",
    )


    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    slot = relationship(
        "AppointmentSlot"
    )


    hold = relationship(
        "SlotHold"
    )

# =========================================================
# 8. PatientIntent
#
# 환자가 실제로 무엇을 찾고 있었는지
#
# 예:
#
# "8월 22일 오후
#  강남에서
#  스마일 시력교정 검진
#  200만원 정도"
# =========================================================

class PatientIntent(Base):

    __tablename__ = "patient_intents"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    # -----------------------------------------------------
    # 모두닥 canonical procedure
    # -----------------------------------------------------

    procedure_code = Column(
        String,
        nullable=False,
        index=True,
    )


    # -----------------------------------------------------
    # 지역
    #
    # 예:
    # 서울
    # -----------------------------------------------------

    region = Column(
        String,
        nullable=True,
    )


    # -----------------------------------------------------
    # 세부 지역
    #
    # 예:
    # 강남구
    # -----------------------------------------------------

    district = Column(
        String,
        nullable=True,
        index=True,
    )


    # -----------------------------------------------------
    # 원하는 날짜
    #
    # 예:
    # 2026-08-22
    # -----------------------------------------------------

    preferred_date = Column(
        Date,
        nullable=True,
    )


    # -----------------------------------------------------
    # 원하는 시간대
    #
    # MORNING
    # AFTERNOON
    # EVENING
    # ANY
    # -----------------------------------------------------

    time_window = Column(
        String,
        nullable=False,
        default="ANY",
    )


    # -----------------------------------------------------
    # 최대 예상 예산
    #
    # 예:
    # 2,000,000원
    # -----------------------------------------------------

    budget_max = Column(
        Integer,
        nullable=True,
    )


    # -----------------------------------------------------
    # 이 intent가 어디서 들어왔는지
    #
    # AI_SIMULATOR
    # CHATGPT_MCP
    # WEB
    # -----------------------------------------------------

    source = Column(
        String,
        nullable=False,
        default="AI_SIMULATOR",
    )


    # -----------------------------------------------------
    # 사용자가 실제로 입력한 원문
    #
    # 나중에:
    # structured intent와 원문을 비교 가능
    # -----------------------------------------------------

    raw_query = Column(
        Text,
        nullable=True,
    )


    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    candidate_matches = relationship(
        "CandidateMatch",
        back_populates="intent",
    )


    decision_events = relationship(
        "DecisionEvent",
        back_populates="intent",
    )


# =========================================================
# 9. CandidateMatch
#
# 하나의 PatientIntent에 대해
# 실제로 어떤 후보들을 보여줬는지 기록
#
# 중요:
# match_score는 의사의 의료적 품질 점수가 아니다.
#
# 사용자가 지정한 조건과 얼마나 맞는지에 대한
# constraint matching score다.
# =========================================================

class CandidateMatch(Base):

    __tablename__ = "candidate_matches"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    intent_id = Column(
        Integer,
        ForeignKey("patient_intents.id"),
        nullable=False,
        index=True,
    )


    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
    )


    offer_id = Column(
        Integer,
        ForeignKey("provider_offers.id"),
        nullable=False,
    )


    # -----------------------------------------------------
    # 이 후보에서 실제로 보여준 가장 빠른 예약 슬롯
    # -----------------------------------------------------

    earliest_slot_id = Column(
        Integer,
        ForeignKey("appointment_slots.id"),
        nullable=True,
    )


    # -----------------------------------------------------
    # Constraint match score
    #
    # 0 ~ 100
    #
    # 의료적 우열 점수가 아님
    # -----------------------------------------------------

    match_score = Column(
        Float,
        nullable=False,
    )


    # 후보 노출 순위
    rank = Column(
        Integer,
        nullable=False,
    )


    # -----------------------------------------------------
    # 왜 이 후보가 나왔는지
    #
    # 예:
    #
    # {
    #   "district_match": true,
    #   "budget_status": "WITHIN_BUDGET",
    #   "availability": "15:00",
    #   "offer_confidence": 0.99
    # }
    # -----------------------------------------------------

    explanation_json = Column(
        JSON,
        nullable=False,
    )


    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    intent = relationship(
        "PatientIntent",
        back_populates="candidate_matches",
    )


    provider = relationship(
        "Provider"
    )


    offer = relationship(
        "ProviderOffer"
    )


    earliest_slot = relationship(
        "AppointmentSlot"
    )


    decision_events = relationship(
        "DecisionEvent",
        back_populates="candidate_match",
    )


# =========================================================
# 10. DecisionEvent
#
# Candidate를 보여준 이후
# 환자가 실제로 어떤 행동을 했는지 기록
#
# 향후:
#
# SHOWN
# SELECTED
# HELD
# CONFIRMED
# CANCELLED
# VISITED
# =========================================================

class DecisionEvent(Base):

    __tablename__ = "decision_events"


    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    intent_id = Column(
        Integer,
        ForeignKey("patient_intents.id"),
        nullable=False,
        index=True,
    )


    candidate_match_id = Column(
        Integer,
        ForeignKey("candidate_matches.id"),
        nullable=True,
    )


    event_type = Column(
        String,
        nullable=False,
        index=True,
    )


    # -----------------------------------------------------
    # Transaction과 연결
    #
    # 처음에는 None일 수 있다.
    # -----------------------------------------------------

    slot_id = Column(
        Integer,
        ForeignKey("appointment_slots.id"),
        nullable=True,
    )


    hold_id = Column(
        Integer,
        ForeignKey("slot_holds.id"),
        nullable=True,
    )


    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=True,
    )


    # -----------------------------------------------------
    # 이벤트별 추가 정보
    # -----------------------------------------------------

    event_metadata = Column(
        JSON,
        nullable=True,
    )


    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    intent = relationship(
        "PatientIntent",
        back_populates="decision_events",
    )


    candidate_match = relationship(
        "CandidateMatch",
        back_populates="decision_events",
    )
