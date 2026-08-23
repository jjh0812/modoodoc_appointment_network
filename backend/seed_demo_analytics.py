import sys

from datetime import date

from app.database import SessionLocal

from app.models import (
    Appointment,
    AppointmentSlot,
    CandidateMatch,
    DecisionEvent,
    PatientIntent,
    SlotHold,
)

from app.models_decision_feedback import (
    DecisionFeedback,
)

from app.services.appointment_service import (
    confirm_slot_hold,
)

from app.services.care_option_match_service import (
    search_care_options as search_care_options_core,
)

from app.services.decision_analytics_service import (
    get_decision_funnel,
)

from app.services.decision_feedback_analytics_service import (
    get_decision_feedback_summary,
)

from app.services.decision_feedback_service import (
    create_no_selection_feedback,
    create_selection_feedback,
)

from app.services.hold_service import (
    create_slot_hold,
)

from app.services.provider_decision_analytics_service import (
    get_hospital_decision_analytics,
)


# =========================================================
# Demo Analytics Dataset
#
# 목적:
#
# 개발 과정에서 뒤섞인 행동 로그 대신
# 사람이 이해하기 쉬운 합성 Demo Dataset을 만든다.
#
#
# 유지:
#
# Hospital
# Provider
# Raw Offer Evidence
# Canonical ProviderOffer
# AppointmentSlot 정의
#
#
# 초기화 후 재생성:
#
# PatientIntent
# CandidateMatch
# DecisionEvent
# DecisionFeedback
# SlotHold
# Appointment
# =========================================================

SOURCE = "DEMO"


DEMO_DATE = date(
    2026,
    8,
    22,
)


# =========================================================
# 최종 목표 Funnel
#
# SEARCHED  = 30
# SHOWN     = 24
# SELECTED  = 10
# HELD      = 10
# CONFIRMED = 5
# =========================================================

SEARCH_WITH_CANDIDATES_COUNT = 24

SEARCH_WITHOUT_CANDIDATES_COUNT = 6

SELECTION_COUNT = 10

CONFIRM_COUNT = 5

NO_SELECTION_FEEDBACK_COUNT = 8


# =========================================================
# 10명의 선택 패턴
#
# Candidate index:
#
# 0 = 1위 후보
# 1 = 2위 후보
# 2 = 3위 후보
#
#
# 일부러 1위만 선택하지 않고
# 세 병원이 모두 선택되게 만든다.
# =========================================================

SELECTION_PLAN = [
    0,
    0,
    1,
    0,
    2,
    1,
    0,
    1,
    2,
    0,
]


# =========================================================
# 첫 5개 Selection은 예약 확정
#
# 나머지 5개는:
#
# SELECTED
# ↓
# HELD
# ↓
# 예약 전 이탈
# =========================================================

CONFIRM_SELECTION_POSITIONS = {
    0,
    1,
    2,
    3,
    4,
}


# =========================================================
# 사용자가 직접 밝힌 Selection Reasons
#
# 10건 기준 목표:
#
# PRICE
# 5 / 10 = 50%
#
# AVAILABILITY
# 4 / 10 = 40%
#
# LOCATION
# 3 / 10 = 30%
#
# DATA_CONFIDENCE
# 2 / 10 = 20%
#
#
# 복수 선택 가능.
# =========================================================

SELECTION_FEEDBACK_PLAN = [
    [
        "PRICE",
        "LOCATION",
    ],

    [
        "PRICE",
    ],

    [
        "AVAILABILITY",
    ],

    [
        "PRICE",
        "LOCATION",
    ],

    [
        "DATA_CONFIDENCE",
    ],

    [
        "PRICE",
        "AVAILABILITY",
    ],

    [
        "LOCATION",
    ],

    [
        "AVAILABILITY",
    ],

    [
        "DATA_CONFIDENCE",
        "AVAILABILITY",
    ],

    [
        "PRICE",
    ],
]


# =========================================================
# 후보는 봤지만 아무것도 선택하지 않은 사용자 중
# 8명의 직접 Feedback
#
# 목표:
#
# BUDGET_TOO_HIGH
# 4 / 8 = 50%
#
# TIME_NOT_MATCH
# 3 / 8 = 37.5%
#
# INSUFFICIENT_INFORMATION
# 2 / 8 = 25%
#
# LOCATION_NOT_MATCH
# 1 / 8 = 12.5%
# =========================================================

NO_SELECTION_FEEDBACK_PLAN = [
    [
        "BUDGET_TOO_HIGH",
    ],

    [
        "TIME_NOT_MATCH",
    ],

    [
        "INSUFFICIENT_INFORMATION",
    ],

    [
        "BUDGET_TOO_HIGH",
        "TIME_NOT_MATCH",
    ],

    [
        "LOCATION_NOT_MATCH",
    ],

    [
        "BUDGET_TOO_HIGH",
    ],

    [
        "TIME_NOT_MATCH",
        "INSUFFICIENT_INFORMATION",
    ],

    [
        "BUDGET_TOO_HIGH",
    ],
]


# =========================================================
# DRY RUN
#
# 기본 실행은 DB를 절대 수정하지 않는다.
#
# Preview:
#
# python seed_demo_analytics.py
#
#
# 실제 적용:
#
# python seed_demo_analytics.py --apply
# =========================================================

if "--apply" not in sys.argv:

    print()

    print(
        "========================================"
    )

    print(
        "DEMO ANALYTICS DATASET PREVIEW"
    )

    print(
        "========================================"
    )

    print()

    print(
        "The database has NOT been modified."
    )

    print()

    print(
        "The following behavior data will be reset:"
    )

    print(
        "- DecisionFeedback"
    )

    print(
        "- DecisionEvent"
    )

    print(
        "- Appointment"
    )

    print(
        "- SlotHold"
    )

    print(
        "- CandidateMatch"
    )

    print(
        "- PatientIntent"
    )

    print()

    print(
        "The following supply data will remain:"
    )

    print(
        "- Hospital"
    )

    print(
        "- Provider"
    )

    print(
        "- Raw Offer Evidence"
    )

    print(
        "- Canonical ProviderOffer"
    )

    print(
        "- AppointmentSlot definitions"
    )

    print()

    print(
        "Target demo funnel:"
    )

    print(
        "SEARCHED : 30"
    )

    print(
        "SHOWN    : 24"
    )

    print(
        "SELECTED : 10"
    )

    print(
        "HELD     : 10"
    )

    print(
        "CONFIRMED: 5"
    )

    print()

    print(
        "Selection feedback:"
    )

    print(
        "10 records"
    )

    print()

    print(
        "No-selection feedback:"
    )

    print(
        "8 records"
    )

    print()

    print(
        "To apply:"
    )

    print(
        "python seed_demo_analytics.py --apply"
    )

    sys.exit(
        0
    )


# =========================================================
# Session helper
# =========================================================

def new_session():

    return SessionLocal()


# =========================================================
# 1. 기존 행동 데이터 초기화
#
# FK 때문에 삭제 순서가 중요하다.
# =========================================================

print()

print(
    "========================================"
)

print(
    "RESET DEMO BEHAVIOR DATA"
)

print(
    "========================================"
)


db = new_session()


try:

    deleted_feedback = (
        db.query(
            DecisionFeedback
        )
        .delete(
            synchronize_session=False
        )
    )


    deleted_events = (
        db.query(
            DecisionEvent
        )
        .delete(
            synchronize_session=False
        )
    )


    deleted_appointments = (
        db.query(
            Appointment
        )
        .delete(
            synchronize_session=False
        )
    )


    deleted_holds = (
        db.query(
            SlotHold
        )
        .delete(
            synchronize_session=False
        )
    )


    deleted_candidates = (
        db.query(
            CandidateMatch
        )
        .delete(
            synchronize_session=False
        )
    )


    deleted_intents = (
        db.query(
            PatientIntent
        )
        .delete(
            synchronize_session=False
        )
    )


    # -----------------------------------------------------
    # Slot 정의 자체는 유지.
    #
    # Transaction 상태만 Demo 시작점으로 초기화.
    # -----------------------------------------------------

    db.query(
        AppointmentSlot
    ).update(
        {
            AppointmentSlot.status:
                "AVAILABLE"
        },
        synchronize_session=False,
    )


    db.commit()


except Exception:

    db.rollback()

    raise


finally:

    db.close()


print(
    "DecisionFeedback:",
    deleted_feedback,
)


print(
    "DecisionEvent:",
    deleted_events,
)


print(
    "Appointment:",
    deleted_appointments,
)


print(
    "SlotHold:",
    deleted_holds,
)


print(
    "CandidateMatch:",
    deleted_candidates,
)


print(
    "PatientIntent:",
    deleted_intents,
)


print(
    "RESET: PASS"
)


# =========================================================
# 2. Search
# =========================================================

def create_search(
    search_number: int,
    budget_max: int,
):

    db = new_session()


    try:

        result = (
            search_care_options_core(

                db=db,

                procedure_code=
                    "VISION_CORRECTION_SMILE",

                district=
                    "강남",

                preferred_date=
                    DEMO_DATE,

                time_window=
                    "AFTERNOON",

                budget_max=
                    budget_max,

                source=
                    SOURCE,

                raw_query=
                    (
                        f"[DEMO #{search_number}] "
                        "강남에서 스마일 시력교정 "
                        "검진 가능한 곳을 찾고 싶습니다."
                    ),

                limit=
                    3,
            )
        )


        return result


    finally:

        db.close()


# =========================================================
# 3. HOLD
# =========================================================

def create_hold(
    candidate: dict,
):

    db = new_session()


    try:

        hold = (
            create_slot_hold(

                db=db,

                slot_id=
                    candidate[
                        "earliest_slot_id"
                    ],

                source=
                    SOURCE,

                candidate_match_id=
                    candidate[
                        "candidate_match_id"
                    ],
            )
        )


        return {
            "id":
                hold.id,

            "slot_id":
                hold.slot_id,

            "status":
                hold.status,
        }


    finally:

        db.close()


# =========================================================
# 4. CONFIRM
# =========================================================

def confirm_hold(
    hold_id: int,
    selection_number: int,
):

    db = new_session()


    try:

        appointment = (
            confirm_slot_hold(

                db=db,

                hold_id=
                    hold_id,

                idempotency_key=
                    (
                        "demo-confirm-"
                        f"{selection_number}"
                    ),
            )
        )


        return appointment.id


    finally:

        db.close()


# =========================================================
# 5. Selection Feedback
# =========================================================

def add_selection_feedback(
    selection_number: int,
    intent_id: int,
    candidate_match_id: int,
    reason_codes: list[str],
):

    db = new_session()


    try:

        feedback = (
            create_selection_feedback(

                db=db,

                intent_id=
                    intent_id,

                candidate_match_id=
                    candidate_match_id,

                reason_codes=
                    reason_codes,

                free_text=
                    "데모용 합성 사용자 피드백",

                source=
                    SOURCE,

                idempotency_key=
                    (
                        "demo-selection-feedback-"
                        f"{selection_number}"
                    ),
            )
        )


        return feedback.id


    finally:

        db.close()


# =========================================================
# 6. No-selection Feedback
# =========================================================

def add_no_selection_feedback(
    feedback_number: int,
    intent_id: int,
    reason_codes: list[str],
):

    db = new_session()


    try:

        feedback = (
            create_no_selection_feedback(

                db=db,

                intent_id=
                    intent_id,

                reason_codes=
                    reason_codes,

                free_text=
                    "데모용 합성 비선택 피드백",

                source=
                    SOURCE,

                idempotency_key=
                    (
                        "demo-no-selection-feedback-"
                        f"{feedback_number}"
                    ),
            )
        )


        return feedback.id


    finally:

        db.close()


# =========================================================
# 7. 예약하지 않은 HOLD를 바로 이탈 상태로 전환
#
# HELD DecisionEvent는 역사적 사실로 남긴다.
#
# 현재 Slot만 다시 AVAILABLE로 풀어
# 다음 Search가 정상적으로 실행되게 한다.
# =========================================================

def abandon_hold(
    hold_id: int,
):

    db = new_session()


    try:

        hold = (
            db.query(
                SlotHold
            )
            .filter(
                SlotHold.id
                == hold_id
            )
            .with_for_update()
            .first()
        )


        if hold is None:

            raise RuntimeError(
                (
                    "Demo hold not found: "
                    f"{hold_id}"
                )
            )


        slot = (
            db.query(
                AppointmentSlot
            )
            .filter(
                AppointmentSlot.id
                == hold.slot_id
            )
            .with_for_update()
            .first()
        )


        hold.status = (
            "EXPIRED"
        )


        if (
            slot is not None
            and
            slot.status
            == "HELD"
        ):

            slot.status = (
                "AVAILABLE"
            )


        db.commit()


    except Exception:

        db.rollback()

        raise


    finally:

        db.close()


# =========================================================
# 8. 후보가 나오는 검색 24건 생성
#
# 중요:
#
# 검색 24건을 먼저 전부 만드는 게 아니라
# 한 건씩 순차 처리한다.
#
# 이유:
#
# 이전 검색의 HOLD / 예약 상태를
# 다음 검색 availability에 반영하기 위해서.
# =========================================================

print()

print(
    "========================================"
)

print(
    "CREATE 24 SEARCHES WITH CANDIDATES"
)

print(
    "========================================"
)


shown_results = []

selected_intent_ids = set()

selection_counter = 0


for search_index in range(
    SEARCH_WITH_CANDIDATES_COUNT
):

    search_number = (
        search_index
        + 1
    )


    result = create_search(

        search_number=
            search_number,

        budget_max=
            2_000_000,
    )


    candidates = (
        result[
            "candidates"
        ]
    )


    if len(candidates) < 3:

        raise RuntimeError(
            (
                "Demo requires at least "
                "3 candidates. "
                f"Search #{search_number} "
                f"returned {len(candidates)}."
            )
        )


    shown_results.append(
        result
    )


    # =====================================================
    # 첫 10개 Search는 실제 선택 발생
    # =====================================================

    if (
        selection_counter
        <
        SELECTION_COUNT
    ):

        candidate_index = (
            SELECTION_PLAN[
                selection_counter
            ]
        )


        candidate = (
            candidates[
                candidate_index
            ]
        )


        hold = (
            create_hold(
                candidate=
                    candidate
            )
        )


        intent_id = (
            result[
                "intent_id"
            ]
        )


        selected_intent_ids.add(
            intent_id
        )


        add_selection_feedback(

            selection_number=
                selection_counter
                + 1,

            intent_id=
                intent_id,

            candidate_match_id=
                candidate[
                    "candidate_match_id"
                ],

            reason_codes=
                SELECTION_FEEDBACK_PLAN[
                    selection_counter
                ],
        )


        # =================================================
        # 첫 5건은 예약 확정
        # =================================================

        if (
            selection_counter
            in
            CONFIRM_SELECTION_POSITIONS
        ):

            confirm_hold(

                hold_id=
                    hold[
                        "id"
                    ],

                selection_number=
                    selection_counter
                    + 1,
            )


            transaction_result = (
                "CONFIRMED"
            )


        # =================================================
        # 나머지 5건은 HOLD 후 이탈
        #
        # Historical HELD Event는 유지.
        # Slot은 다시 AVAILABLE.
        # =================================================

        else:

            abandon_hold(
                hold_id=
                    hold[
                        "id"
                    ]
            )


            transaction_result = (
                "ABANDONED_AFTER_HOLD"
            )


        print(
            (
                f"SEARCH #{search_number}: "
                f"SELECTED "
                f"{candidate['hospital_name']} "
                f"-> {transaction_result}"
            )
        )


        selection_counter += 1


    else:

        print(
            (
                f"SEARCH #{search_number}: "
                "SHOWN -> NO SELECTION"
            )
        )


print()

print(
    "SEARCHES WITH CANDIDATES:",
    len(
        shown_results
    ),
)


print(
    "SELECTIONS:",
    selection_counter,
)


# =========================================================
# 9. 선택하지 않은 14건 중
#    8건에 직접 비선택 이유 저장
# =========================================================

no_selection_results = [

    result

    for result
    in shown_results

    if (
        result[
            "intent_id"
        ]
        not in
        selected_intent_ids
    )
]


if (
    len(
        no_selection_results
    )
    != 14
):

    raise RuntimeError(
        (
            "Expected 14 no-selection "
            "shown intents, got "
            f"{len(no_selection_results)}"
        )
    )


for (
    feedback_index,
    reasons,
) in enumerate(
    NO_SELECTION_FEEDBACK_PLAN
):

    result = (
        no_selection_results[
            feedback_index
        ]
    )


    add_no_selection_feedback(

        feedback_number=
            feedback_index
            + 1,

        intent_id=
            result[
                "intent_id"
            ],

        reason_codes=
            reasons,
    )


print()

print(
    "NO-SELECTION FEEDBACK:",
    len(
        NO_SELECTION_FEEDBACK_PLAN
    ),
)


# =========================================================
# 10. 후보 자체가 없는 검색 6건
#
# 매우 낮은 예산으로
# executable candidate가 나오지 않게 한다.
# =========================================================

print()

print(
    "========================================"
)

print(
    "CREATE 6 SEARCHES WITHOUT CANDIDATES"
)

print(
    "========================================"
)


empty_count = 0


for index in range(
    SEARCH_WITHOUT_CANDIDATES_COUNT
):

    result = create_search(

        search_number=
            (
                SEARCH_WITH_CANDIDATES_COUNT
                + index
                + 1
            ),

        budget_max=
            100_000,
    )


    candidate_count = len(
        result[
            "candidates"
        ]
    )


    if (
        candidate_count
        != 0
    ):

        raise RuntimeError(
            (
                "Expected zero candidates "
                "for low-budget search, got "
                f"{candidate_count}"
            )
        )


    empty_count += 1


    print(
        (
            f"EMPTY SEARCH #{index + 1}: "
            "0 candidates"
        )
    )


print()

print(
    "SEARCHES WITHOUT CANDIDATES:",
    empty_count,
)


# =========================================================
# 11. 최종 Analytics 검증
# =========================================================

db = new_session()


try:

    funnel = (
        get_decision_funnel(
            db=db
        )
    )


    feedback_summary = (
        get_decision_feedback_summary(
            db=db
        )
    )


    hospital_analytics = (
        get_hospital_decision_analytics(
            db=db
        )
    )


finally:

    db.close()


# =========================================================
# 12. 결과 출력
# =========================================================

print()

print(
    "========================================"
)

print(
    "FINAL DEMO ANALYTICS"
)

print(
    "========================================"
)


print()

print(
    "FUNNEL:"
)

print(
    funnel[
        "funnel"
    ]
)


print()

print(
    "CONVERSION:"
)

print(
    funnel[
        "conversion_rates_pct"
    ]
)


print()

print(
    "SELECTION REASONS:"
)

print(
    feedback_summary[
        "selection_feedback"
    ]
)


print()

print(
    "NO-SELECTION REASONS:"
)

print(
    feedback_summary[
        "no_selection_feedback"
    ]
)


print()

print(
    "HOSPITALS:"
)


for hospital in (
    hospital_analytics[
        "hospitals"
    ]
):

    print(
        (
            hospital[
                "hospital_name"
            ],
            hospital[
                "funnel"
            ],
            hospital[
                "conversion_rates_pct"
            ],
        )
    )


# =========================================================
# 13. 최종 PASS 검증
# =========================================================

actual_funnel = (
    funnel[
        "funnel"
    ]
)


selection_feedback_count = (
    feedback_summary[
        "selection_feedback"
    ][
        "feedback_count"
    ]
)


no_selection_feedback_count = (
    feedback_summary[
        "no_selection_feedback"
    ][
        "feedback_count"
    ]
)


passed = (

    actual_funnel[
        "searched"
    ]
    == 30

    and

    actual_funnel[
        "shown"
    ]
    == 24

    and

    actual_funnel[
        "selected"
    ]
    == 10

    and

    actual_funnel[
        "held"
    ]
    == 10

    and

    actual_funnel[
        "confirmed"
    ]
    == 5

    and

    selection_feedback_count
    == 10

    and

    no_selection_feedback_count
    == 8
)


print()


if passed:

    print(
        "DEMO ANALYTICS DATASET: PASS"
    )

else:

    print(
        "DEMO ANALYTICS DATASET: FAIL"
    )