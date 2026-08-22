import json
import uuid

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
    DecisionEvent,
    SlotHold,
)


# =========================================================
# 테스트 설정
# =========================================================

REQUEST_COUNT = 100

BASE_URL = "http://127.0.0.1:8001"

TEST_SOURCE = (
    "IDEMPOTENCY_CONCURRENCY_TEST"
)


# =========================================================
# 이번 테스트에서만 사용하는
# 고유 Idempotency Key
#
# 같은 테스트 실행 안에서는
# 100개 요청 모두 이 Key를 공유한다.
#
# 하지만 다음번 테스트 실행 때는
# 새로운 Key가 생성된다.
# =========================================================

IDEMPOTENCY_KEY = (
    "concurrency-test-"
    + str(
        uuid.uuid4()
    )
)


# =========================================================
# 1. 테스트용 AVAILABLE Slot 선택
#
# 중요:
#
# 예전 테스트처럼
#
# db.query(Appointment).delete()
#
# 를 하지 않는다.
#
# 그 이유:
#
# 실제 Transaction Graph의
# DecisionEvent가 기존 Appointment를
# FK로 참조하고 있기 때문이다.
#
#
# 이제는:
#
# 기존 데이터 유지
#      ↓
# AVAILABLE Slot 하나 선택
#      ↓
# 그 Slot만 테스트
#
# 방식으로 간다.
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
# 2. 먼저 정상 HOLD 하나 생성
#
# CONFIRM하려면 ACTIVE HOLD가 필요하다.
#
# Candidate-aware HOLD가 아니다.
#
# 따라서 이 테스트의 목적은
#
# Transaction Graph 테스트가 아니라
#
# 순수하게:
#
# HOLD
#   ↓
# 100 concurrent CONFIRM
#   ↓
# Appointment 정확히 1개
#
# 를 확인하는 것이다.
# =========================================================

hold_body = {

    "source":
        TEST_SOURCE,
}


hold_data = json.dumps(
    hold_body
).encode(
    "utf-8"
)


hold_request = Request(

    (
        f"{BASE_URL}"
        f"/slots/{SLOT_ID}/hold"
    ),

    data=
        hold_data,

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

    body = (
        error
        .read()
        .decode(
            "utf-8"
        )
    )

    raise RuntimeError(
        (
            "Failed to create test HOLD. "
            f"HTTP {error.code}: {body}"
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
# 3. 100개 CONFIRM 요청을
#    최대한 동시에 출발시키기 위한 Barrier
# =========================================================

start_barrier = Barrier(
    REQUEST_COUNT
)


# =========================================================
# 4. 같은 예약 확정 요청 하나 보내기
#
# 핵심:
#
# 100개 요청 전부
#
# 동일:
#
# hold_id
# idempotency_key
#
# 를 사용한다.
# =========================================================

def send_confirm_request(
    request_number: int,
):

    body = {

        "idempotency_key":
            IDEMPOTENCY_KEY,
    }


    data = json.dumps(
        body
    ).encode(
        "utf-8"
    )


    request = Request(

        (
            f"{BASE_URL}"
            f"/holds/{hold_id}/confirm"
        ),

        data=
            data,

        headers={
            "Content-Type":
                "application/json",
        },

        method=
            "POST",
    )


    # -----------------------------------------------------
    # 100개 thread가 모두 준비될 때까지 대기
    #
    # 준비가 끝나면 거의 동시에 서버로 출발
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
                .decode(
                    "utf-8"
                )
            )


            return (
                response.status,
                response_body,
            )


    # -----------------------------------------------------
    # 서버가 4xx / 5xx HTTP 응답을 반환
    # -----------------------------------------------------

    except HTTPError as error:

        response_body = (
            error
            .read()
            .decode(
                "utf-8"
            )
        )


        return (
            error.code,
            response_body,
        )


    # -----------------------------------------------------
    # timeout / connection error 등
    #
    # HTTP status조차 받지 못한 경우
    # -----------------------------------------------------

    except Exception as error:

        return (
            "ERROR",
            str(
                error
            ),
        )


# =========================================================
# 5. 100개 CONFIRM 요청 동시 실행
# =========================================================

with ThreadPoolExecutor(
    max_workers=
        REQUEST_COUNT
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
# =========================================================

status_breakdown = Counter(

    str(
        status
    )

    for status, _
    in results
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
    dict(
        status_breakdown
    ),
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

    for status, _
    in results

    if status == 200
)


conflict_count = sum(

    1

    for status, _
    in results

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
# 정상이라면:
#
# 100개의 HTTP 200 응답
#
# 전부 같은 Appointment ID
# =========================================================

appointment_ids = set()


for status, body in results:

    if status == 200:

        parsed = json.loads(
            body
        )


        appointment_ids.add(
            parsed[
                "id"
            ]
        )


# =========================================================
# 9. 실제 PostgreSQL DB 확인
# =========================================================

db = SessionLocal()

try:

    appointment_count = (

        db.query(
            Appointment
        )
        .filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        )
        .count()
    )


    appointment = (

        db.query(
            Appointment
        )
        .filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        )
        .first()
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
    # Session을 닫기 전에 필요한 값들을 복사
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


    if appointment is not None:

        appointment_snapshot = {

            "id":
                appointment.id,

            "slot_id":
                appointment.slot_id,

            "hold_id":
                appointment.hold_id,

            "source":
                appointment.source,

            "idempotency_key":
                appointment.idempotency_key,

            "status":
                appointment.status,
        }


    else:

        appointment_snapshot = None


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
    slot_status,
)


print(
    "HOLD STATUS:",
    hold_status,
)


if appointment_snapshot is not None:

    print(
        "APPOINTMENT:",
        appointment_snapshot[
            "id"
        ],
        appointment_snapshot[
            "slot_id"
        ],
        appointment_snapshot[
            "hold_id"
        ],
        appointment_snapshot[
            "source"
        ],
        appointment_snapshot[
            "idempotency_key"
        ],
        appointment_snapshot[
            "status"
        ],
    )


# =========================================================
# 11. 최종 PASS / FAIL 판정
# =========================================================

passed = (

    success_count
    == 100

    and

    conflict_count
    == 0

    and

    other_count
    == 0

    and

    len(
        appointment_ids
    )
    == 1

    and

    appointment_count
    == 1

    and

    slot_status
    == "CONFIRMED"

    and

    hold_status
    == "CONFIRMED"
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


# =========================================================
# 12. TEST DATA CLEANUP
#
# 중요:
#
# 예전처럼 모든 Appointment / Hold를
# 삭제하지 않는다.
#
#
# 이번 테스트가 만든 것만:
#
# 1. DecisionEvent
# 2. Appointment
# 3. SlotHold
#
# 순서로 삭제한다.
#
# 마지막으로 테스트 Slot을 AVAILABLE로 복구.
#
#
# 기존 MCP Transaction Graph:
#
# SHOWN
# SELECTED
# HELD
# CONFIRMED
#
# 데이터는 건드리지 않는다.
# =========================================================

cleanup_db = SessionLocal()


try:

    # -----------------------------------------------------
    # 혹시 이번 테스트 Hold / Appointment를 참조하는
    # DecisionEvent가 생겼다면 먼저 제거
    #
    # 일반 direct HOLD에서는 생성되지 않지만,
    # FK 안전성을 위해 방어적으로 처리한다.
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
    # 이번 테스트 Appointment만 제거
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
    # 혹시 다른 Appointment / Hold가
    # 같은 Slot을 사용하는지 확인
    #
    # 아무것도 없을 때만 AVAILABLE로 복구한다.
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


    print()

    print(
        "TEST DATA CLEANUP: PASS"
    )


except Exception:

    cleanup_db.rollback()

    raise


finally:

    cleanup_db.close()