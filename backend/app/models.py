from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)

from datetime import datetime
from sqlalchemy.orm import relationship

from app.database import Base


# =========================================================
# 1. Provider
#
# 병원의 의사
# =========================================================

class Provider(Base):

    __tablename__ = "providers"

    # 의사 번호
    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # 의사 이름
    name = Column(
        String,
        nullable=False,
    )

    # 진료 분야
    specialty = Column(
        String,
        nullable=False,
    )

    # 이 의사가 가지고 있는 예약 시간 슬롯들
    slots = relationship(
        "AppointmentSlot",
        back_populates="provider",
    )


# =========================================================
# 2. AppointmentSlot
#
# 의사의 실제 예약 시간
# =========================================================

class AppointmentSlot(Base):

    __tablename__ = "appointment_slots"

    # 예약 슬롯 번호
    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # 어느 의사의 예약시간인지
    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
    )

    # 예약 시간
    start_time = Column(
        DateTime,
        nullable=False,
    )

    # 현재 예약 상태
    # AVAILABLE / HELD / CONFIRMED 등을 나중에 사용
    status = Column(
        String,
        nullable=False,
        default="AVAILABLE",
    )

    # 이 슬롯의 의사 정보
    provider = relationship(
        "Provider",
        back_populates="slots",
    )

# =========================================================
# 3. SlotHold
#
# AI 또는 사용자가 예약 자리를
# 잠시 확보해두는 기록
# =========================================================

class SlotHold(Base):

    __tablename__ = "slot_holds"

    # Hold 자체의 번호
    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # 어떤 예약 슬롯을 잡았는지
    slot_id = Column(
        Integer,
        ForeignKey("appointment_slots.id"),
        nullable=False,
    )

    # 어디에서 들어온 요청인지
    # 예: ChatGPT / Modoodoc / Naver AI
    source = Column(
        String,
        nullable=False,
    )

    # Hold가 언제 만료되는지
    expires_at = Column(
        DateTime,
        nullable=False,
    )

    # ACTIVE / EXPIRED / CONFIRMED
    status = Column(
        String,
        nullable=False,
        default="ACTIVE",
    )

    # 해당 예약 슬롯과 연결
    slot = relationship(
        "AppointmentSlot"
    )


# =========================================================
# 실제 확정 예약
# =========================================================

class Appointment(Base):

    __tablename__ = "appointments"


    # -----------------------------------------------------
    # 예약 자체의 번호
    # -----------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )


    # -----------------------------------------------------
    # 어떤 예약 슬롯인지
    #
    # 하나의 슬롯에는 하나의 확정 예약만 허용
    # -----------------------------------------------------

    slot_id = Column(
        Integer,
        ForeignKey("appointment_slots.id"),
        nullable=False,
        unique=True,
    )


    # -----------------------------------------------------
    # 어떤 HOLD를 확정한 것인지
    #
    # 같은 HOLD를 두 번 예약으로 만들 수 없음
    # -----------------------------------------------------

    hold_id = Column(
        Integer,
        ForeignKey("slot_holds.id"),
        nullable=False,
        unique=True,
    )


    # -----------------------------------------------------
    # 예약 요청이 어디서 들어왔는지
    #
    # 예:
    # ChatGPT
    # Gemini
    # Modoodoc Web
    # -----------------------------------------------------

    source = Column(
        String,
        nullable=False,
    )


    # -----------------------------------------------------
    # 동일 요청 재시도 방지용 키
    #
    # 나중에 AI가 같은 요청을 100번 retry해도
    # 실제 예약은 1개만 생성되게 하는 핵심
    # -----------------------------------------------------

    idempotency_key = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )


    # -----------------------------------------------------
    # 예약 상태
    # -----------------------------------------------------

    status = Column(
        String,
        nullable=False,
        default="CONFIRMED",
    )


    # -----------------------------------------------------
    # 예약 확정 시각
    # -----------------------------------------------------

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    # -----------------------------------------------------
    # 관계
    # -----------------------------------------------------

    slot = relationship(
        "AppointmentSlot"
    )

    hold = relationship(
        "SlotHold"
    )