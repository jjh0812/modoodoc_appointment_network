import json
import uuid

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
    "IDEMPOTENCY_KEY_REUSE_TEST"
)

IDEMPOTENCY_KEY = (
    "idempotency-reuse-test-"
    + str(
        uuid.uuid4()
    )
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
        ).encode(
            "utf-8"
        ),
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )


    try:

        with urlopen(
            request,
            timeout=30,
        ) as response:

            raw_body = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )


            return (
                response.status,
                json.loads(
                    raw_body
                ),
            )


    except HTTPError as error:

        raw_body = (
            error
            .read()
            .decode(
                "utf-8"
            )
        )


        try:

            parsed_body = (
                json.loads(
                    raw_body
                )
            )

        except json.JSONDecodeError:

            parsed_body = {
                "raw":
                    raw_body,
            }


        return (
            error.code,
            parsed_body,
        )


# =========================================================
# 1. AVAILABLE Slot 두 개 선택
#
# 중요:
#
# 기존 Appointment / Hold를 전부 삭제하지 않는다.
#
# 기존 MCP / Web transaction은 그대로 보존한다.
# =========================================================

db = SessionLocal()

try:

    slots = (
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
        .limit(
            2
        )
        .all()
    )


    if len(slots) < 2:

        raise RuntimeError(
            "At least 2 AVAILABLE slots are required"
        )


    SLOT_1_ID = (
        slots[0].id
    )

    SLOT_2_ID = (
        slots[1].id
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
    "SLOT 1:",
    SLOT_1_ID,
)

print(
    "SLOT 2:",
    SLOT_2_ID,
)

print(
    "IDEMPOTENCY KEY:",
    IDEMPOTENCY_KEY,
)

print(
    "TEST SLOT SELECTION: PASS"
)


# =========================================================
# 테스트 도중 만들어진 Hold 추적
#
# 마지막 cleanup에서 이것들만 삭제한다.
# =========================================================

hold_ids = []


try:

    # =====================================================
    # 2. 첫 번째 Slot HOLD
    # =====================================================

    hold_1_status, hold_1_body = (
        post_json(

            (
                f"{BASE_URL}"
                f"/slots/{SLOT_1_ID}/hold"
            ),

            {
                "source":
                    TEST_SOURCE,
            },
        )
    )


    if hold_1_status != 200:

        raise RuntimeError(
            (
                "First HOLD failed: "
                f"{hold_1_status} "
                f"{hold_1_body}"
            )
        )


    HOLD_1_ID = (
        hold_1_body[
            "id"
        ]
    )


    hold_ids.append(
        HOLD_1_ID
    )


    print()

    print(
        "FIRST HOLD CREATED:",
        HOLD_1_ID,
    )


    # =====================================================
    # 3. 두 번째 Slot HOLD
    # =====================================================

    hold_2_status, hold_2_body = (
        post_json(

            (
                f"{BASE_URL}"
                f"/slots/{SLOT_2_ID}/hold"
            ),

            {
                "source":
                    TEST_SOURCE,
            },
        )
    )


    if hold_2_status != 200:

        raise RuntimeError(
            (
                "Second HOLD failed: "
                f"{hold_2_status} "
                f"{hold_2_body}"
            )
        )


    HOLD_2_ID = (
        hold_2_body[
            "id"
        ]
    )


    hold_ids.append(
        HOLD_2_ID
    )


    print(
        "SECOND HOLD CREATED:",
        HOLD_2_ID,
    )


    # =====================================================
    # 4. 첫 번째 Hold CONFIRM
    #
    # 같은 IDEMPOTENCY_KEY를 사용한다.
    #
    # 이 요청은 정상 성공해야 한다.
    # =====================================================

    first_confirm_status, first_confirm_body = (
        post_json(

            (
                f"{BASE_URL}"
                f"/holds/{HOLD_1_ID}/confirm"
            ),

            {
                "idempotency_key":
                    IDEMPOTENCY_KEY,
            },
        )
    )


    print()

    print(
        "========================================"
    )

    print(
        "FIRST CONFIRM"
    )

    print(
        "========================================"
    )

    print(
        "STATUS:",
        first_confirm_status,
    )

    print(
        "BODY:",
        json.dumps(
            first_confirm_body,
            ensure_ascii=False,
        ),
    )


    # =====================================================
    # 5. 전혀 다른 Hold에
    #    동일 Idempotency Key 재사용
    #
    # 반드시 409로 막혀야 한다.
    # =====================================================

    second_confirm_status, second_confirm_body = (
        post_json(

            (
                f"{BASE_URL}"
                f"/holds/{HOLD_2_ID}/confirm"
            ),

            {
                "idempotency_key":
                    IDEMPOTENCY_KEY,
            },
        )
    )


    print()

    print(
        "========================================"
    )

    print(
        "SECOND CONFIRM WITH SAME KEY"
    )

    print(
        "========================================"
    )

    print(
        "STATUS:",
        second_confirm_status,
    )

    print(
        "BODY:",
        json.dumps(
            second_confirm_body,
            ensure_ascii=False,
        ),
    )


    # =====================================================
    # 6. PostgreSQL 상태 확인
    #
    # 전체 Appointment가 아니라
    # 이번 테스트 key만 검사한다.
    # =====================================================

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


        hold_1 = (
            db.query(
                SlotHold
            )
            .filter(
                SlotHold.id
                == HOLD_1_ID
            )
            .first()
        )


        hold_2 = (
            db.query(
                SlotHold
            )
            .filter(
                SlotHold.id
                == HOLD_2_ID
            )
            .first()
        )


        slot_1 = (
            db.query(
                AppointmentSlot
            )
            .filter(
                AppointmentSlot.id
                == SLOT_1_ID
            )
            .first()
        )


        slot_2 = (
            db.query(
                AppointmentSlot
            )
            .filter(
                AppointmentSlot.id
                == SLOT_2_ID
            )
            .first()
        )


        appointment_id = (
            appointment.id
            if appointment is not None
            else None
        )


        appointment_hold_id = (
            appointment.hold_id
            if appointment is not None
            else None
        )


        hold_1_status_db = (
            hold_1.status
            if hold_1 is not None
            else None
        )


        hold_2_status_db = (
            hold_2.status
            if hold_2 is not None
            else None
        )


        slot_1_status_db = (
            slot_1.status
            if slot_1 is not None
            else None
        )


        slot_2_status_db = (
            slot_2.status
            if slot_2 is not None
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
        appointment_count,
    )

    print(
        "APPOINTMENT ID:",
        appointment_id,
    )

    print(
        "APPOINTMENT HOLD ID:",
        appointment_hold_id,
    )

    print(
        "FIRST HOLD STATUS:",
        hold_1_status_db,
    )

    print(
        "SECOND HOLD STATUS:",
        hold_2_status_db,
    )

    print(
        "FIRST SLOT STATUS:",
        slot_1_status_db,
    )

    print(
        "SECOND SLOT STATUS:",
        slot_2_status_db,
    )


    # =====================================================
    # 7. 두 번째 응답 detail 확인
    # =====================================================

    second_detail = (
        second_confirm_body.get(
            "detail"
        )
        if isinstance(
            second_confirm_body,
            dict,
        )
        else None
    )


    # =====================================================
    # 8. 최종 PASS / FAIL
    #
    # 첫 Hold:
    # CONFIRMED
    #
    # 두 번째 Hold:
    # 동일 key 때문에 CONFIRM 거부
    # 따라서 여전히 ACTIVE
    #
    # 첫 Slot:
    # CONFIRMED
    #
    # 두 번째 Slot:
    # HELD
    # =====================================================

    passed = (

        first_confirm_status
        == 200

        and

        second_confirm_status
        == 409

        and

        second_detail
        ==
        (
            "Idempotency key already used "
            "for another hold"
        )

        and

        appointment_count
        == 1

        and

        appointment_hold_id
        == HOLD_1_ID

        and

        hold_1_status_db
        == "CONFIRMED"

        and

        hold_2_status_db
        == "ACTIVE"

        and

        slot_1_status_db
        == "CONFIRMED"

        and

        slot_2_status_db
        == "HELD"
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


# =========================================================
# 9. 반드시 테스트 데이터 cleanup
#
# 테스트가 PASS든 FAIL이든
# finally에서 이번 테스트 데이터만 제거한다.
# =========================================================

finally:

    cleanup_db = SessionLocal()


    try:

        # -------------------------------------------------
        # 혹시 이번 Hold들과 연결된
        # DecisionEvent가 있으면 먼저 제거
        # -------------------------------------------------

        if hold_ids:

            cleanup_db.query(
                DecisionEvent
            ).filter(
                DecisionEvent.hold_id.in_(
                    hold_ids
                )
            ).delete(
                synchronize_session=False
            )


        # -------------------------------------------------
        # 이번 테스트 Key의 Appointment만 제거
        # -------------------------------------------------

        cleanup_db.query(
            Appointment
        ).filter(
            Appointment.idempotency_key
            == IDEMPOTENCY_KEY
        ).delete(
            synchronize_session=False
        )


        # -------------------------------------------------
        # 이번 테스트 Hold들만 제거
        # -------------------------------------------------

        if hold_ids:

            cleanup_db.query(
                SlotHold
            ).filter(
                SlotHold.id.in_(
                    hold_ids
                )
            ).delete(
                synchronize_session=False
            )


        # -------------------------------------------------
        # 테스트 Slot 두 개를 원래 사용할 수 있는 상태로 복구
        #
        # 단, 다른 Appointment/Hold가 없을 때만.
        # -------------------------------------------------

        for slot_id in (
            SLOT_1_ID,
            SLOT_2_ID,
        ):

            remaining_appointments = (
                cleanup_db.query(
                    Appointment
                )
                .filter(
                    Appointment.slot_id
                    == slot_id
                )
                .count()
            )


            remaining_holds = (
                cleanup_db.query(
                    SlotHold
                )
                .filter(
                    SlotHold.slot_id
                    == slot_id
                )
                .count()
            )


            slot = (
                cleanup_db.query(
                    AppointmentSlot
                )
                .filter(
                    AppointmentSlot.id
                    == slot_id
                )
                .with_for_update()
                .first()
            )


            if (
                slot is not None
                and
                remaining_appointments == 0
                and
                remaining_holds == 0
            ):

                slot.status = (
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