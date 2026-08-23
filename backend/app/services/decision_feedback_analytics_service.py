from collections import Counter

from sqlalchemy.orm import Session

from app.models import (
    CandidateMatch,
    Provider,
)

from app.models_decision_feedback import (
    DecisionFeedback,
)


# =========================================================
# Percentage helper
# =========================================================

def percentage(
    numerator: int,
    denominator: int,
) -> float:

    if denominator == 0:
        return 0.0

    return round(
        (
            numerator
            / denominator
        )
        * 100,
        1,
    )


# =========================================================
# reason_codes 집계
#
# DecisionFeedback는 복수 선택 가능:
#
# ["PRICE", "LOCATION"]
#
# 따라서 reason percentage 합계가
# 100%를 넘을 수 있다.
# =========================================================

def aggregate_reason_codes(
    feedback_rows: list[
        DecisionFeedback
    ],
) -> dict:

    counter = Counter()


    for feedback in feedback_rows:

        reason_codes = (
            feedback.reason_codes
            or []
        )


        for reason_code in reason_codes:

            counter[
                reason_code
            ] += 1


    feedback_count = len(
        feedback_rows
    )


    reasons = []


    for (
        reason_code,
        count,
    ) in counter.most_common():

        reasons.append(
            {
                "reason_code":
                    reason_code,

                "count":
                    count,

                "feedback_share_pct":
                    percentage(
                        count,
                        feedback_count,
                    ),
            }
        )


    return {
        "feedback_count":
            feedback_count,

        "reasons":
            reasons,
    }


# =========================================================
# 1. 전체 Decision Feedback Summary
#
# 질문:
#
# 선택한 사람들은 왜 골랐나?
#
# 아무것도 안 고른 사람들은
# 왜 선택하지 않았나?
# =========================================================

def get_decision_feedback_summary(
    db: Session,
) -> dict:

    # =====================================================
    # Selection Feedback
    # =====================================================

    selection_feedback = (
        db.query(
            DecisionFeedback
        )
        .filter(
            DecisionFeedback.feedback_type
            == "SELECTION_REASON"
        )
        .order_by(
            DecisionFeedback.id.asc()
        )
        .all()
    )


    # =====================================================
    # No-selection Feedback
    # =====================================================

    no_selection_feedback = (
        db.query(
            DecisionFeedback
        )
        .filter(
            DecisionFeedback.feedback_type
            == "NO_SELECTION_REASON"
        )
        .order_by(
            DecisionFeedback.id.asc()
        )
        .all()
    )


    selection_summary = (
        aggregate_reason_codes(
            selection_feedback
        )
    )


    no_selection_summary = (
        aggregate_reason_codes(
            no_selection_feedback
        )
    )


    # =====================================================
    # Response
    # =====================================================

    return {

        "total_feedback":
            (
                len(
                    selection_feedback
                )
                +
                len(
                    no_selection_feedback
                )
            ),

        "selection_feedback":
            selection_summary,

        "no_selection_feedback":
            no_selection_summary,

        "note":
            (
                "Reason shares use feedback records "
                "as the denominator. "
                "Because users may select multiple reasons, "
                "percentages can sum to more than 100%."
            ),
    }


# =========================================================
# 2. 특정 병원의 Selection Reasons
#
# 중요한 점:
#
# NO_SELECTION_REASON은
# candidate_match_id가 NULL이므로
# 특정 병원의 비선택 이유로 귀속하지 않는다.
#
# 여기서는 해당 병원이 실제 SELECTED된
# Candidate의 직접 Feedback만 집계한다.
# =========================================================

def get_hospital_selection_reasons(
    db: Session,
    hospital_id: int,
) -> dict:

    rows = (
        db.query(
            DecisionFeedback,
            CandidateMatch,
            Provider,
        )
        .join(
            CandidateMatch,
            DecisionFeedback.candidate_match_id
            == CandidateMatch.id,
        )
        .join(
            Provider,
            CandidateMatch.provider_id
            == Provider.id,
        )
        .filter(
            DecisionFeedback.feedback_type
            == "SELECTION_REASON",

            Provider.hospital_id
            == hospital_id,
        )
        .order_by(
            DecisionFeedback.id.asc()
        )
        .all()
    )


    feedback_rows = [
        feedback

        for (
            feedback,
            candidate,
            provider,
        ) in rows
    ]


    summary = (
        aggregate_reason_codes(
            feedback_rows
        )
    )


    return {

        "hospital_id":
            hospital_id,

        "selection_feedback_count":
            summary[
                "feedback_count"
            ],

        "reasons":
            summary[
                "reasons"
            ],

        "note":
            (
                "These are explicit reasons reported "
                "for candidates from this hospital "
                "that were actually selected."
            ),
    }