import json

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

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

REQUEST_COUNT = 100

BASE_URL = "http://127.0.0.1:8001"

SLOT_ID = 1

IDEMPOTENCY_KEY = (
    "ChatGPT-confirm-concurrency-001"
)


# =========================================================
# 1. 테스트 DB 초기화
#
# 기존 테스트 Appointment / Hold 삭제
# Slot #1은 AVAILABLE로 복구
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
# 2. 먼저 정상 HOLD 하나 생성
#
# CONFIRM하려면 ACTIVE HOLD가 하나 필요함
# =========================================================

hold_body = {
    "source": "ChatGPT"
}


hold_data = json.dumps(
    hold_body
).encode("utf-8")


hold_request = Request(
    f"{BASE_URL}/slots/{SLOT_ID}/hold",
    data=hold_data,
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
    hold_id,
)


# =========================================================
# 3. 100개 CONFIRM 요청을
#    최대한 동시에 출발시키기 위한 Barrier
# =========================================================

start_barrier = Barrier(
    REQUEST_COUNT
)


# =========================================================
# 4. 같은 예약 확정 요청 하나 보내기
# =========================================================

def send_confirm_request(
    request_number: int,
):

    body = {
        "idempotency_key": (
            IDEMPOTENCY_KEY
        )
    }


    data = json.dumps(
        body
    ).encode("utf-8")


    request = Request(
        (
            f"{BASE_URL}"
            f"/holds/{hold_id}/confirm"
        ),
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )


    # -----------------------------------------------------
    # 100개 thread가 모두 준비될 때까지 대기
    #
    # 100개가 준비되면 거의 동시에 출발
    # -----------------------------------------------------

    start_barrier.wait()


    try:

        with urlopen(
            request,
            timeout=30,
        ) as response:

            response_body = (
                response
                .read()
                .decode("utf-8")
            )


            return (
                response.status,
                response_body,
            )


    # -----------------------------------------------------
    # 서버가 4xx / 5xx HTTP 응답을 반환한 경우
    # -----------------------------------------------------

    except HTTPError as error:

        response_body = (
            error
            .read()
            .decode("utf-8")
        )


        return (
            error.code,
            response_body,
        )


    # -----------------------------------------------------
    # timeout / connection error 등
    # HTTP status조차 받지 못한 경우
    # -----------------------------------------------------

    except Exception as error:

        return (
            "ERROR",
            str(error),
        )


# =========================================================
# 5. 100개 CONFIRM 요청 동시 실행
# =========================================================

with ThreadPoolExecutor(
    max_workers=REQUEST_COUNT
) as executor:

    results = list(
        executor.map(
            send_confirm_request,
            range(
                1,
                REQUEST_COUNT + 1,
            ),
        )
    )


# =========================================================
# 6. RAW HTTP 결과 진단
#
# 지금 필요한 핵심 부분
#
# OTHER 100의 정체가:
#
# 500인지
# ERROR인지
# timeout인지
#
# 확인한다.
# =========================================================

status_breakdown = Counter(
    str(status)
    for status, _ in results
)


print()

print(
    "========================================"
)

print(
    "RAW RESPONSE DIAGNOSTICS"
)

print(
    "========================================"
)


print(
    "RAW STATUS BREAKDOWN:",
    dict(status_breakdown),
)


print()

print(
    "FIRST 10 NON-200 RESPONSES:"
)


shown = 0


for status, body in results:

    if status != 200:

        print(
            "STATUS:",
            status,
        )

        print(
            "BODY:",
            body,
        )

        print(
            "--------------------"
        )


        shown += 1


        if shown >= 10:
            break


# =========================================================
# 7. HTTP 결과 집계
# =========================================================

success_count = sum(
    1
    for status, _ in results
    if status == 200
)


conflict_count = sum(
    1
    for status, _ in results
    if status == 409
)


other_count = (
    REQUEST_COUNT
    - success_count
    - conflict_count
)


# =========================================================
# 8. 200 응답들의 Appointment ID 확인
#
# 정상이라면 100개의 200 응답 모두
# 같은 Appointment ID를 반환해야 함
# =========================================================

appointment_ids = set()


for status, body in results:

    if status == 200:

        parsed = json.loads(
            body
        )

        appointment_ids.add(
            parsed["id"]
        )


# =========================================================
# 9. 실제 PostgreSQL DB 확인
# =========================================================

db = SessionLocal()

try:

    appointment_count = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        )
        .count()
    )


    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        )
        .first()
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


# =========================================================
# 10. 결과 출력
# =========================================================

print()

print(
    "========================================"
)

print(
    "CONCURRENT IDEMPOTENCY TEST RESULT"
)

print(
    "========================================"
)


print(
    "TOTAL REQUESTS:",
    REQUEST_COUNT,
)


print(
    "200 SUCCESS:",
    success_count,
)


print(
    "409 CONFLICT:",
    conflict_count,
)


print(
    "OTHER:",
    other_count,
)


print(
    "UNIQUE APPOINTMENT IDS:",
    appointment_ids,
)


print(
    "DB APPOINTMENT COUNT:",
    appointment_count,
)


print(
    "SLOT STATUS:",
    slot.status,
)


print(
    "HOLD STATUS:",
    hold.status,
)


if appointment is not None:

    print(
        "APPOINTMENT:",
        appointment.id,
        appointment.slot_id,
        appointment.hold_id,
        appointment.source,
        appointment.idempotency_key,
        appointment.status,
    )


# =========================================================
# 11. 최종 PASS / FAIL
# =========================================================

passed = (
    success_count == 100
    and conflict_count == 0
    and other_count == 0
    and len(appointment_ids) == 1
    and appointment_count == 1
    and slot.status == "CONFIRMED"
    and hold.status == "CONFIRMED"
)


print()


if passed:

    print(
        "CONCURRENT IDEMPOTENCY: PASS"
    )

else:

    print(
        "CONCURRENT IDEMPOTENCY: FAIL"
    )