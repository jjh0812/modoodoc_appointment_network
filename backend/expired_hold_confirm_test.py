import json

from datetime import datetime, timedelta

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
# 설정
# =========================================================

BASE_URL = "http://127.0.0.1:8001"

SLOT_ID = 1


# =========================================================
# 1. 테스트 초기화
# =========================================================

db = SessionLocal()

try:

    db.query(Appointment).delete()

    db.query(SlotHold).delete()


    slot = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id == SLOT_ID
        )
        .first()
    )


    if slot is None:

        raise RuntimeError(
            "Slot #1 not found"
        )


    slot.status = "AVAILABLE"

    db.commit()

finally:

    db.close()


print(
    "TEST RESET: PASS"
)


# =========================================================
# 2. 정상 HOLD 생성
# =========================================================

hold_body = {
    "source": "ChatGPT"
}


hold_request = Request(
    f"{BASE_URL}/slots/{SLOT_ID}/hold",
    data=json.dumps(
        hold_body
    ).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
    },
    method="POST",
)


with urlopen(
    hold_request,
    timeout=30,
) as response:

    hold_response = json.loads(
        response
        .read()
        .decode("utf-8")
    )


hold_id = hold_response["id"]


print(
    "HOLD CREATED:",
    hold_id
)


# =========================================================
# 3. HOLD를 강제로 과거 시각으로 변경
#
# 실제로 5분 기다릴 필요 없이
# "이미 만료된 HOLD" 상황을 만든다.
# =========================================================

db = SessionLocal()

try:

    hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.id == hold_id
        )
        .first()
    )


    hold.expires_at = (
        datetime.utcnow()
        - timedelta(seconds=10)
    )


    db.commit()

finally:

    db.close()


print(
    "HOLD FORCED TO EXPIRE: PASS"
)


# =========================================================
# 4. 만료된 HOLD를 CONFIRM 시도
# =========================================================

confirm_body = {
    "idempotency_key":
        "expired-hold-confirm-001"
}


confirm_request = Request(
    (
        f"{BASE_URL}"
        f"/holds/{hold_id}/confirm"
    ),
    data=json.dumps(
        confirm_body
    ).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
    },
    method="POST",
)


status = None
response_body = None


try:

    with urlopen(
        confirm_request,
        timeout=30,
    ) as response:

        status = response.status

        response_body = (
            response
            .read()
            .decode("utf-8")
        )


except HTTPError as error:

    status = error.code

    response_body = (
        error
        .read()
        .decode("utf-8")
    )


print(
    "CONFIRM STATUS:",
    status
)

print(
    "CONFIRM BODY:",
    response_body
)


# =========================================================
# 5. 실제 DB 상태 확인
# =========================================================

db = SessionLocal()

try:

    appointment_count = (
        db.query(Appointment)
        .count()
    )


    slot = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.id == SLOT_ID
        )
        .first()
    )


    hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.id == hold_id
        )
        .first()
    )

finally:

    db.close()


print(
    "APPOINTMENT COUNT:",
    appointment_count
)

print(
    "SLOT STATUS:",
    slot.status
)

print(
    "HOLD STATUS:",
    hold.status
)


# =========================================================
# 6. 최종 판정
# =========================================================

passed = (
    status == 409
    and appointment_count == 0
    and slot.status == "AVAILABLE"
    and hold.status == "EXPIRED"
)


if passed:

    print(
        "EXPIRED HOLD CONFIRM: PASS"
    )

else:

    print(
        "EXPIRED HOLD CONFIRM: FAIL"
    )