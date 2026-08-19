import json

from datetime import datetime

from urllib.error import HTTPError
from urllib.request import (
    Request,
    urlopen,
)

from app.database import SessionLocal

from app.models import (
    Appointment,
    AppointmentSlot,
    SlotHold,
)


# =========================================================
# 테스트 설정
# =========================================================

BASE_URL = "http://127.0.0.1:8001"

PROVIDER_ID = 1

SLOT_1_ID = 1

IDEMPOTENCY_KEY = (
    "shared-idempotency-key-001"
)


# =========================================================
# HTTP POST helper
# =========================================================

def post_json(
    url: str,
    body: dict,
):

    request = Request(
        url,
        data=json.dumps(
            body
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )


    try:

        with urlopen(
            request,
            timeout=30,
        ) as response:

            return (
                response.status,
                response
                .read()
                .decode("utf-8"),
            )


    except HTTPError as error:

        return (
            error.code,
            error
            .read()
            .decode("utf-8"),
        )


# =========================================================
# 1. 테스트 DB 초기화
# =========================================================

db = SessionLocal()

try:

    # 기존 예약부터 삭제
    db.query(Appointment).delete()

    # 기존 HOLD 삭제
    db.query(SlotHold).delete()


    # -----------------------------------------------------
    # 첫 번째 슬롯
    # -----------------------------------------------------

    slot_1 = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id == SLOT_1_ID
        )
        .first()
    )


    if slot_1 is None:

        raise RuntimeError(
            "Slot #1 not found"
        )


    slot_1.status = "AVAILABLE"


    # -----------------------------------------------------
    # 두 번째 테스트 슬롯 찾기
    #
    # 없으면 새로 생성
    # -----------------------------------------------------

    second_slot_time = datetime(
        2026,
        8,
        22,
        15,
        0,
        0,
    )


    slot_2 = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.provider_id
            == PROVIDER_ID,
            AppointmentSlot.start_time
            == second_slot_time,
        )
        .first()
    )


    if slot_2 is None:

        slot_2 = AppointmentSlot(
            provider_id=PROVIDER_ID,
            start_time=second_slot_time,
            status="AVAILABLE",
        )

        db.add(
            slot_2
        )

        db.flush()


    slot_2.status = "AVAILABLE"


    db.commit()


    slot_2_id = slot_2.id

finally:

    db.close()


print(
    "TEST RESET: PASS"
)

print(
    "SLOT 1:",
    SLOT_1_ID
)

print(
    "SLOT 2:",
    slot_2_id
)


# =========================================================
# 2. 첫 번째 슬롯 HOLD
# =========================================================

status, body = post_json(
    f"{BASE_URL}/slots/{SLOT_1_ID}/hold",
    {
        "source": "ChatGPT",
    },
)


if status != 200:

    raise RuntimeError(
        f"First HOLD failed: {status} {body}"
    )


hold_1 = json.loads(
    body
)

hold_1_id = hold_1["id"]


print(
    "FIRST HOLD CREATED:",
    hold_1_id
)


# =========================================================
# 3. 첫 번째 HOLD 예약 확정
#
# shared-idempotency-key-001 사용
# =========================================================

first_confirm_status, first_confirm_body = (
    post_json(
        (
            f"{BASE_URL}"
            f"/holds/{hold_1_id}/confirm"
        ),
        {
            "idempotency_key":
                IDEMPOTENCY_KEY,
        },
    )
)


print(
    "FIRST CONFIRM STATUS:",
    first_confirm_status
)

print(
    "FIRST CONFIRM BODY:",
    first_confirm_body
)


# =========================================================
# 4. 두 번째 슬롯 HOLD
# =========================================================

status, body = post_json(
    f"{BASE_URL}/slots/{slot_2_id}/hold",
    {
        "source": "Gemini",
    },
)


if status != 200:

    raise RuntimeError(
        f"Second HOLD failed: {status} {body}"
    )


hold_2 = json.loads(
    body
)

hold_2_id = hold_2["id"]


print(
    "SECOND HOLD CREATED:",
    hold_2_id
)


# =========================================================
# 5. 다른 HOLD에 같은 idempotency_key 사용
#
# 이 요청은 반드시 409가 나와야 한다.
# =========================================================

second_confirm_status, second_confirm_body = (
    post_json(
        (
            f"{BASE_URL}"
            f"/holds/{hold_2_id}/confirm"
        ),
        {
            "idempotency_key":
                IDEMPOTENCY_KEY,
        },
    )
)


print(
    "SECOND CONFIRM STATUS:",
    second_confirm_status
)

print(
    "SECOND CONFIRM BODY:",
    second_confirm_body
)


# =========================================================
# 6. PostgreSQL 실제 상태 확인
# =========================================================

db = SessionLocal()

try:

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        )
        .all()
    )


    slot_1 = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id
            == SLOT_1_ID
        )
        .first()
    )


    slot_2 = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id
            == slot_2_id
        )
        .first()
    )


    hold_1 = (
        db.query(SlotHold)
        .filter(
            SlotHold.id
            == hold_1_id
        )
        .first()
    )


    hold_2 = (
        db.query(SlotHold)
        .filter(
            SlotHold.id
            == hold_2_id
        )
        .first()
    )


finally:

    db.close()


print()
print(
    "========================================"
)

print(
    "IDEMPOTENCY KEY REUSE TEST RESULT"
)

print(
    "========================================"
)


print(
    "APPOINTMENT COUNT:",
    len(appointments)
)

print(
    "SLOT 1 STATUS:",
    slot_1.status
)

print(
    "HOLD 1 STATUS:",
    hold_1.status
)

print(
    "SLOT 2 STATUS:",
    slot_2.status
)

print(
    "HOLD 2 STATUS:",
    hold_2.status
)


# =========================================================
# 7. 최종 PASS / FAIL
# =========================================================

passed = (
    first_confirm_status == 200

    and second_confirm_status == 409

    and len(appointments) == 1

    and appointments[0].hold_id == hold_1_id

    and slot_1.status == "CONFIRMED"

    and hold_1.status == "CONFIRMED"

    and slot_2.status == "HELD"

    and hold_2.status == "ACTIVE"
)


print()


if passed:

    print(
        "IDEMPOTENCY KEY REUSE: PASS"
    )

else:

    print(
        "IDEMPOTENCY KEY REUSE: FAIL"
    )