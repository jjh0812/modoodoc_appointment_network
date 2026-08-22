import json
import uuid

from urllib.error import HTTPError
from urllib.request import (
    Request,
    urlopen,
)

from app.database import SessionLocal

from app.models import (
    CandidateMatch,
    DecisionEvent,
    PatientIntent,
)

from app.models_decision_feedback import (
    DecisionFeedback,
)


# =========================================================
# 설정
# =========================================================

BASE_URL = "http://127.0.0.1:8001"


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
            body,
            ensure_ascii=False,
        ).encode("utf-8"),
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

            raw = (
                response
                .read()
                .decode("utf-8")
            )


            return (
                response.status,
                json.loads(raw),
            )


    except HTTPError as error:

        raw = (
            error
            .read()
            .decode("utf-8")
        )


        return (
            error.code,
            json.loads(raw),
        )


# =========================================================
# 1. 테스트 대상 자동 탐색
#
# A:
# SELECTED Event가 실제 존재하는 Intent/Candidate
#
# B:
# SHOWN은 있지만 SELECTED가 없는 Intent
# =========================================================

db = SessionLocal()

try:

    # -----------------------------------------------------
    # Selection Feedback 테스트 대상
    # -----------------------------------------------------

    selected_event = (
        db.query(
            DecisionEvent
        )
        .filter(
            DecisionEvent.event_type
            == "SELECTED"
        )
        .order_by(
            DecisionEvent.id.desc()
        )
        .first()
    )


    if selected_event is None:

        raise RuntimeError(
            "No SELECTED event found"
        )


    selection_intent_id = (
        selected_event.intent_id
    )

    selection_candidate_id = (
        selected_event.candidate_match_id
    )


    # -----------------------------------------------------
    # No-selection Feedback 테스트 대상
    #
    # PatientIntent 중:
    #
    # SHOWN 있음
    # SELECTED 없음
    # -----------------------------------------------------

    intents = (
        db.query(
            PatientIntent
        )
        .order_by(
            PatientIntent.id.desc()
        )
        .all()
    )


    no_selection_intent_id = None


    for intent in intents:

        shown_exists = (
            db.query(
                DecisionEvent
            )
            .filter(
                DecisionEvent.intent_id
                == intent.id,

                DecisionEvent.event_type
                == "SHOWN",
            )
            .first()
            is not None
        )


        selected_exists = (
            db.query(
                DecisionEvent
            )
            .filter(
                DecisionEvent.intent_id
                == intent.id,

                DecisionEvent.event_type
                == "SELECTED",
            )
            .first()
            is not None
        )


        if (
            shown_exists
            and
            not selected_exists
        ):

            no_selection_intent_id = (
                intent.id
            )

            break


    if no_selection_intent_id is None:

        raise RuntimeError(
            "No suitable no-selection intent found"
        )


finally:

    db.close()


print()

print(
    "========================================"
)

print(
    "TEST TARGETS"
)

print(
    "========================================"
)


print(
    "SELECTION INTENT:",
    selection_intent_id,
)


print(
    "SELECTION CANDIDATE:",
    selection_candidate_id,
)


print(
    "NO-SELECTION INTENT:",
    no_selection_intent_id,
)


# =========================================================
# 2. 이번 테스트 전용 Idempotency Key
# =========================================================

selection_key = (
    "feedback-selection-test-"
    + str(uuid.uuid4())
)


no_selection_key = (
    "feedback-no-selection-test-"
    + str(uuid.uuid4())
)


# =========================================================
# 3. Selection Feedback 저장
#
# "가격 + 예약시간 때문에 선택"
# =========================================================

selection_body = {

    "intent_id":
        selection_intent_id,

    "candidate_match_id":
        selection_candidate_id,

    "reason_codes": [
        "PRICE",
        "AVAILABILITY",
    ],

    "free_text":
        "예산 안이고 가능한 시간이 있어서 선택했습니다.",

    "source":
        "DECISION_FEEDBACK_TEST",

    "idempotency_key":
        selection_key,
}


selection_status, selection_response = (
    post_json(
        (
            f"{BASE_URL}"
            "/decision-feedback/selection"
        ),
        selection_body,
    )
)


print()

print(
    "========================================"
)

print(
    "SELECTION FEEDBACK"
)

print(
    "========================================"
)


print(
    "STATUS:",
    selection_status,
)


print(
    json.dumps(
        selection_response,
        ensure_ascii=False,
        indent=2,
    )
)


# =========================================================
# 4. 같은 Selection Feedback retry
#
# 새 레코드가 아니라
# 같은 Feedback을 반환해야 함
# =========================================================

retry_status, retry_response = (
    post_json(
        (
            f"{BASE_URL}"
            "/decision-feedback/selection"
        ),
        selection_body,
    )
)


print()

print(
    "========================================"
)

print(
    "SELECTION FEEDBACK RETRY"
)

print(
    "========================================"
)


print(
    "STATUS:",
    retry_status,
)


print(
    json.dumps(
        retry_response,
        ensure_ascii=False,
        indent=2,
    )
)


# =========================================================
# 5. No-selection Feedback 저장
#
# "정보 부족 때문에 아무 후보도 선택 안 함"
# =========================================================

no_selection_body = {

    "intent_id":
        no_selection_intent_id,

    "reason_codes": [
        "INSUFFICIENT_INFORMATION",
    ],

    "free_text":
        "비교 정보가 더 필요해서 아직 선택하지 않았습니다.",

    "source":
        "DECISION_FEEDBACK_TEST",

    "idempotency_key":
        no_selection_key,
}


no_selection_status, no_selection_response = (
    post_json(
        (
            f"{BASE_URL}"
            "/decision-feedback/no-selection"
        ),
        no_selection_body,
    )
)


print()

print(
    "========================================"
)

print(
    "NO-SELECTION FEEDBACK"
)

print(
    "========================================"
)


print(
    "STATUS:",
    no_selection_status,
)


print(
    json.dumps(
        no_selection_response,
        ensure_ascii=False,
        indent=2,
    )
)


# =========================================================
# 6. PostgreSQL 검증
# =========================================================

db = SessionLocal()

try:

    selection_count = (
        db.query(
            DecisionFeedback
        )
        .filter(
            DecisionFeedback.idempotency_key
            == selection_key
        )
        .count()
    )


    no_selection_count = (
        db.query(
            DecisionFeedback
        )
        .filter(
            DecisionFeedback.idempotency_key
            == no_selection_key
        )
        .count()
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
    "SELECTION FEEDBACK COUNT:",
    selection_count,
)


print(
    "NO-SELECTION FEEDBACK COUNT:",
    no_selection_count,
)


# =========================================================
# 7. PASS / FAIL
# =========================================================

passed = (

    selection_status == 200

    and

    retry_status == 200

    and

    no_selection_status == 200

    and

    selection_response["id"]
    ==
    retry_response["id"]

    and

    selection_count == 1

    and

    no_selection_count == 1
)


print()


if passed:

    print(
        "DECISION FEEDBACK END-TO-END: PASS"
    )

else:

    print(
        "DECISION FEEDBACK END-TO-END: FAIL"
    )


# =========================================================
# 8. 테스트 데이터 Cleanup
#
# 실제 기존 Transaction Graph는 보존하고
# 이번 테스트가 만든 Feedback만 삭제한다.
# =========================================================

cleanup_db = SessionLocal()

try:

    cleanup_db.query(
        DecisionFeedback
    ).filter(
        DecisionFeedback.idempotency_key.in_(
            [
                selection_key,
                no_selection_key,
            ]
        )
    ).delete(
        synchronize_session=False
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