import json
import uuid

from datetime import (
    datetime,
    timedelta,
)

from urllib.error import HTTPError

from urllib.request import (
    Request,
    urlopen,
)

from app.database import SessionLocal

from app.models import (
    Appointment,
    AppointmentSlot,
    DecisionEvent,
    SlotHold,
)


# =========================================================
# 설정
# =========================================================

BASE_URL = (
    "http://127.0.0.1:8001"
)


TEST_SOURCE = (
    "EXPIRED_HOLD_CONFIRM_TEST"
)


# =========================================================
# 이번 테스트 전용 Idempotency Key
#
# 기존 MCP / Web 예약과 절대로 충돌하지 않게
# 매 실행마다 새로운 UUID 사용
# =========================================================

IDEMPOTENCY_KEY = (
    "expired-hold-test-"
    + str(
        uuid.uuid4()
    )
)


# =========================================================
# 1. AVAILABLE Slot 하나 선택
#
# 중요:
#
# 예전처럼
#
# db.query(Appointment).delete()
# db.query(SlotHold).delete()
#
# 하지 않는다.
#
# 기존 Transaction Graph와
# 실제 테스트 데이터를 그대로 보존한다.
# =========================================================

db = SessionLocal()

try:

    slot = (
        db.query(
            AppointmentSlot
        )
        .filter(
            AppointmentSlot.status
            == "AVAILABLE"
        )
        .order_by(
            AppointmentSlot.id.asc()
        )
        .first()
    )


    if slot is None:

        raise RuntimeError(
            "No AVAILABLE slot found for test"
        )


    SLOT_ID = (
        slot.id
    )


finally:

    db.close()


print()

print(
    "========================================"
)

print(
    "TEST SLOT SELECTION"
)

print(
    "========================================"
)


print(
    "SLOT ID:",
    SLOT_ID,
)


print(
    "IDEMPOTENCY KEY:",
    IDEMPOTENCY_KEY,
)


print(
    "TEST SLOT SELECTION: PASS"
)


# =========================================================
# 2. 정상 HOLD 생성
#
# Candidate-aware HOLD가 아닌
# 순수 예약-engine 테스트용 HOLD
# =========================================================

hold_body = {

    "source":
        TEST_SOURCE,
}


hold_request = Request(

    (
        f"{BASE_URL}"
        f"/slots/{SLOT_ID}/hold"
    ),

    data=json.dumps(
        hold_body
    ).encode(
        "utf-8"
    ),

    headers={
        "Content-Type":
            "application/json",
    },

    method=
        "POST",
)


try:

    with urlopen(
        hold_request,
        timeout=30,
    ) as response:

        hold_response = json.loads(

            response
            .read()
            .decode(
                "utf-8"
            )
        )


except HTTPError as error:

    error_body = (
        error
        .read()
        .decode(
            "utf-8"
        )
    )


    raise RuntimeError(
        (
            "Failed to create test HOLD. "
            f"HTTP {error.code}: "
            f"{error_body}"
        )
    )


hold_id = (
    hold_response[
        "id"
    ]
)


print()

print(
    "HOLD CREATED:",
    hold_id,
)


# =========================================================
# 3. HOLD를 강제로 만료시킨다.
#
# 실제 5분을 기다리지 않고:
#
# expires_at = 현재보다 10초 전
#
# 으로 만든다.
# =========================================================

db = SessionLocal()

try:

    hold = (
        db.query(
            SlotHold
        )
        .filter(
            SlotHold.id
            == hold_id
        )
        .first()
    )


    if hold is None:

        raise RuntimeError(
            "Test hold not found"
        )


    hold.expires_at = (

        datetime.utcnow()
        - timedelta(
            seconds=10
        )
    )


    db.commit()


finally:

    db.close()


print(
    "HOLD FORCED TO EXPIRE: PASS"
)


# =========================================================
# 4. 이미 만료된 HOLD를 CONFIRM 시도
#
# 정상 동작:
#
# HTTP 409
#
# {
#     "detail": "Hold is not active"
# }
#
# 그리고 DB에서는:
#
# Hold:
# ACTIVE → EXPIRED
#
# Slot:
# HELD → AVAILABLE
#
# Appointment:
# 생성되지 않음
# =========================================================

confirm_body = {

    "idempotency_key":
        IDEMPOTENCY_KEY,
}


confirm_request = Request(

    (
        f"{BASE_URL}"
        f"/holds/{hold_id}/confirm"
    ),

    data=json.dumps(
        confirm_body
    ).encode(
        "utf-8"
    ),

    headers={
        "Content-Type":
            "application/json",
    },

    method=
        "POST",
)


status = None

response_body = None


try:

    with urlopen(
        confirm_request,
        timeout=30,
    ) as response:

        status = (
            response.status
        )


        response_body = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )


except HTTPError as error:

    status = (
        error.code
    )


    response_body = (
        error
        .read()
        .decode(
            "utf-8"
        )
    )


print()

print(
    "========================================"
)

print(
    "EXPIRED HOLD CONFIRM RESPONSE"
)

print(
    "========================================"
)


print(
    "CONFIRM STATUS:",
    status,
)


print(
    "CONFIRM BODY:",
    response_body,
)


# =========================================================
# 5. Response의 detail 확인
# =========================================================

response_detail = None


if response_body:

    try:

        parsed_response = (
            json.loads(
                response_body
            )
        )


        response_detail = (
            parsed_response.get(
                "detail"
            )
        )


    except json.JSONDecodeError:

        response_detail = None


# =========================================================
# 6. 실제 PostgreSQL 상태 확인
#
# 중요:
#
# 전체 Appointment 개수를 세지 않는다.
#
# 이번 테스트의 고유 idempotency_key로
# 생성된 Appointment만 확인한다.
# =========================================================

db = SessionLocal()

try:

    test_appointment_count = (

        db.query(
            Appointment
        )
        .filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        )
        .count()
    )


    slot = (
        db.query(
            AppointmentSlot
        )
        .filter(
            AppointmentSlot.id
            == SLOT_ID
        )
        .first()
    )


    hold = (
        db.query(
            SlotHold
        )
        .filter(
            SlotHold.id
            == hold_id
        )
        .first()
    )


    # -----------------------------------------------------
    # Session 닫기 전에 필요한 값을 복사
    # -----------------------------------------------------

    slot_status = (

        slot.status
        if slot is not None
        else None
    )


    hold_status = (

        hold.status
        if hold is not None
        else None
    )


finally:

    db.close()


print()

print(
    "========================================"
)

print(
    "DATABASE RESULT"
)

print(
    "========================================"
)


print(
    "TEST APPOINTMENT COUNT:",
    test_appointment_count,
)


print(
    "SLOT STATUS:",
    slot_status,
)


print(
    "HOLD STATUS:",
    hold_status,
)


# =========================================================
# 7. 최종 판정
#
# 반드시:
#
# HTTP 409
# detail = Hold is not active
# Appointment = 0
# Slot = AVAILABLE
# Hold = EXPIRED
# =========================================================

passed = (

    status
    == 409

    and

    response_detail
    == "Hold is not active"

    and

    test_appointment_count
    == 0

    and

    slot_status
    == "AVAILABLE"

    and

    hold_status
    == "EXPIRED"
)


print()


if passed:

    print(
        "EXPIRED HOLD CONFIRM: PASS"
    )


else:

    print(
        "EXPIRED HOLD CONFIRM: FAIL"
    )


# =========================================================
# 8. 테스트 데이터만 CLEANUP
#
# 기존:
#
# MCP 예약
# Web 예약
# Transaction Graph
#
# 는 절대로 삭제하지 않는다.
#
#
# 이번 테스트가 만든 데이터만:
#
# DecisionEvent
#     ↓
# Appointment
#     ↓
# SlotHold
#
# 순서로 제거한다.
# =========================================================

cleanup_db = SessionLocal()


try:

    # -----------------------------------------------------
    # 현재 direct HOLD에서는
    # DecisionEvent가 생성되지 않지만
    #
    # FK 안전성을 위해 방어적으로 제거한다.
    # -----------------------------------------------------

    cleanup_db.query(
        DecisionEvent
    ).filter(
        DecisionEvent.hold_id
        == hold_id
    ).delete(
        synchronize_session=False
    )


    # -----------------------------------------------------
    # 혹시 잘못해서 Appointment가 생성됐더라도
    # 이번 테스트 key의 Appointment만 제거
    # -----------------------------------------------------

    cleanup_db.query(
        Appointment
    ).filter(
        Appointment.idempotency_key
        == IDEMPOTENCY_KEY
    ).delete(
        synchronize_session=False
    )


    # -----------------------------------------------------
    # 이번 테스트 Hold만 제거
    # -----------------------------------------------------

    cleanup_db.query(
        SlotHold
    ).filter(
        SlotHold.id
        == hold_id
    ).delete(
        synchronize_session=False
    )


    # -----------------------------------------------------
    # 이 Slot을 다른 Appointment / Hold가
    # 사용하는지 확인
    # -----------------------------------------------------

    remaining_appointment_count = (

        cleanup_db.query(
            Appointment
        )
        .filter(
            Appointment.slot_id
            == SLOT_ID
        )
        .count()
    )


    remaining_hold_count = (

        cleanup_db.query(
            SlotHold
        )
        .filter(
            SlotHold.slot_id
            == SLOT_ID
        )
        .count()
    )


    test_slot = (

        cleanup_db.query(
            AppointmentSlot
        )
        .filter(
            AppointmentSlot.id
            == SLOT_ID
        )
        .with_for_update()
        .first()
    )


    # -----------------------------------------------------
    # 다른 transaction이 이 Slot을 사용하지 않을 때만
    # AVAILABLE 상태로 복구
    # -----------------------------------------------------

    if (
        test_slot is not None
        and
        remaining_appointment_count == 0
        and
        remaining_hold_count == 0
    ):

        test_slot.status = (
            "AVAILABLE"
        )


    cleanup_db.commit()


    print(
        "TEST DATA CLEANUP: PASS"
    )


except Exception:

    cleanup_db.rollback()

    raise


finally:

    cleanup_db.close()