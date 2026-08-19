from datetime import datetime

from pydantic import BaseModel, ConfigDict


# =========================================================
# AppointmentSlot API 응답 형태
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
# Slot Hold 요청
#
# 누가 이 슬롯을 잡으려고 하는가?
# =========================================================

class SlotHoldRequest(BaseModel):

    source: str


# =========================================================
# Slot Hold 응답
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
# 예약 확정 요청
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
# 예약 확정 결과
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