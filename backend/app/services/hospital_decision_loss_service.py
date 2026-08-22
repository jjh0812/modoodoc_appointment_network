from sqlalchemy.orm import Session

from app.models import (
    CandidateMatch,
    DecisionEvent,
    Hospital,
    Provider,
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
# 안전한 score 변환
# =========================================================

def score_value(
    candidate: CandidateMatch,
) -> float:

    if candidate.match_score is None:
        return 0.0

    return float(
        candidate.match_score
    )


# =========================================================
# explanation_json에서 budget status 읽기
# =========================================================

def get_budget_status(
    candidate: CandidateMatch,
):

    explanation = (
        candidate.explanation_json
        or {}
    )

    return explanation.get(
        "budget_status"
    )


# =========================================================
# Hospital Decision Loss Analysis
#
# 질문:
#
# "이 병원이 후보로 노출됐는데,
#  실제 선택 단계에서는 어떻게 됐나?"
#
#
# 중요한 구분:
#
# SHOWN만 있고 아무도 선택하지 않은 검색
#     =
# 아직 병원이 '졌다'고 말할 수 없음
#
# SHOWN 후 다른 병원이 SELECTED
#     =
# 비교 가능한 decision loss
# =========================================================

def get_hospital_decision_loss(
    db: Session,
    hospital_id: int,
):

    # =====================================================
    # 1. 병원 확인
    # =====================================================

    hospital = (
        db.query(
            Hospital
        )
        .filter(
            Hospital.id
            == hospital_id
        )
        .first()
    )


    if hospital is None:

        return None


    # =====================================================
    # 2. 이 병원이 SHOWN된 Candidate들
    #
    # DecisionEvent
    #     ↓
    # CandidateMatch
    #     ↓
    # Provider
    #     ↓
    # Hospital
    # =====================================================

    shown_rows = (
        db.query(
            DecisionEvent,
            CandidateMatch,
            Provider,
        )
        .join(
            CandidateMatch,
            DecisionEvent.candidate_match_id
            == CandidateMatch.id,
        )
        .join(
            Provider,
            CandidateMatch.provider_id
            == Provider.id,
        )
        .filter(
            DecisionEvent.event_type
            == "SHOWN",

            Provider.hospital_id
            == hospital_id,
        )
        .order_by(
            DecisionEvent.id.asc()
        )
        .all()
    )


    # =====================================================
    # 3. Intent당 이 병원의 대표 Candidate
    #
    # 한 검색에서 같은 병원 후보가 여러 개면
    # rank가 가장 높은(숫자가 가장 작은) 후보 사용.
    # =====================================================

    shown_by_intent = {}


    for (
        event,
        candidate,
        provider,
    ) in shown_rows:

        intent_id = (
            event.intent_id
        )


        existing = (
            shown_by_intent.get(
                intent_id
            )
        )


        if existing is None:

            shown_by_intent[
                intent_id
            ] = {
                "event":
                    event,

                "candidate":
                    candidate,

                "provider":
                    provider,
            }

            continue


        existing_candidate = (
            existing[
                "candidate"
            ]
        )


        existing_rank = (
            existing_candidate.rank
            if existing_candidate.rank
            is not None
            else 999999
        )


        new_rank = (
            candidate.rank
            if candidate.rank
            is not None
            else 999999
        )


        if new_rank < existing_rank:

            shown_by_intent[
                intent_id
            ] = {
                "event":
                    event,

                "candidate":
                    candidate,

                "provider":
                    provider,
            }


    # =====================================================
    # 4. 실제 SELECTED event 조회
    #
    # 동일 Intent에 SELECTED가 여러 개 있다면
    # 가장 최신 selection을 사용한다.
    # =====================================================

    selected_rows = (
        db.query(
            DecisionEvent,
            CandidateMatch,
            Provider,
            Hospital,
        )
        .join(
            CandidateMatch,
            DecisionEvent.candidate_match_id
            == CandidateMatch.id,
        )
        .join(
            Provider,
            CandidateMatch.provider_id
            == Provider.id,
        )
        .join(
            Hospital,
            Provider.hospital_id
            == Hospital.id,
        )
        .filter(
            DecisionEvent.event_type
            == "SELECTED"
        )
        .order_by(
            DecisionEvent.id.asc()
        )
        .all()
    )


    selected_by_intent = {}


    for (
        event,
        candidate,
        provider,
        selected_hospital,
    ) in selected_rows:

        selected_by_intent[
            event.intent_id
        ] = {
            "event":
                event,

            "candidate":
                candidate,

            "provider":
                provider,

            "hospital":
                selected_hospital,
        }


    # =====================================================
    # 5. 집계 변수
    # =====================================================

    shown_intents = len(
        shown_by_intent
    )

    decision_opportunities = 0

    selected_by_this_hospital = 0

    lost_to_other_candidate = 0

    no_selection_after_exposure = 0


    signal_counts = {

        "not_top1":
            0,

        "lower_rank_than_selected":
            0,

        "lower_score_than_selected":
            0,

        "budget_partial_match":
            0,
    }


    lost_cases = []


    total_rank_gap = 0

    total_score_gap = 0.0


    # =====================================================
    # 6. Intent별 분석
    # =====================================================

    for (
        intent_id,
        shown_info,
    ) in shown_by_intent.items():

        hospital_candidate = (
            shown_info[
                "candidate"
            ]
        )


        selected_info = (
            selected_by_intent.get(
                intent_id
            )
        )


        # -------------------------------------------------
        # 아무 후보도 선택되지 않은 검색
        #
        # 이걸 loss라고 부르면 안 된다.
        # -------------------------------------------------

        if selected_info is None:

            no_selection_after_exposure += 1

            continue


        decision_opportunities += 1


        selected_candidate = (
            selected_info[
                "candidate"
            ]
        )


        selected_hospital = (
            selected_info[
                "hospital"
            ]
        )


        # -------------------------------------------------
        # 이 병원이 실제 선택됨
        # -------------------------------------------------

        if (
            selected_hospital.id
            == hospital_id
        ):

            selected_by_this_hospital += 1

            continue


        # -------------------------------------------------
        # 다른 병원이 선택됨
        #
        # 여기부터 실제 비교 가능한 loss case
        # -------------------------------------------------

        lost_to_other_candidate += 1


        signals = []


        hospital_rank = (
            hospital_candidate.rank
        )


        selected_rank = (
            selected_candidate.rank
        )


        hospital_score = (
            score_value(
                hospital_candidate
            )
        )


        selected_score = (
            score_value(
                selected_candidate
            )
        )


        budget_status = (
            get_budget_status(
                hospital_candidate
            )
        )


        # =================================================
        # Signal 1
        # Top-1이 아니었음
        # =================================================

        if (
            hospital_rank is not None
            and
            hospital_rank != 1
        ):

            signal_counts[
                "not_top1"
            ] += 1

            signals.append(
                "NOT_TOP1"
            )


        # =================================================
        # Signal 2
        # 실제 선택된 후보보다 rank가 낮음
        # =================================================

        if (
            hospital_rank is not None
            and
            selected_rank is not None
            and
            hospital_rank > selected_rank
        ):

            signal_counts[
                "lower_rank_than_selected"
            ] += 1

            signals.append(
                "LOWER_RANK_THAN_SELECTED"
            )


            total_rank_gap += (
                hospital_rank
                - selected_rank
            )


        # =================================================
        # Signal 3
        # 실제 선택된 후보보다 constraint score가 낮음
        # =================================================

        if (
            hospital_score
            < selected_score
        ):

            signal_counts[
                "lower_score_than_selected"
            ] += 1

            signals.append(
                "LOWER_SCORE_THAN_SELECTED"
            )


            total_score_gap += (
                selected_score
                - hospital_score
            )


        # =================================================
        # Signal 4
        # 예산이 완전 일치가 아니라 PARTIAL_MATCH
        # =================================================

        if (
            budget_status
            == "PARTIAL_MATCH"
        ):

            signal_counts[
                "budget_partial_match"
            ] += 1

            signals.append(
                "BUDGET_PARTIAL_MATCH"
            )


        # =================================================
        # Case Detail
        # =================================================

        lost_cases.append(
            {
                "intent_id":
                    intent_id,

                "hospital_candidate": {

                    "candidate_match_id":
                        hospital_candidate.id,

                    "rank":
                        hospital_rank,

                    "constraint_match_score":
                        hospital_score,

                    "budget_status":
                        budget_status,
                },

                "selected_candidate": {

                    "candidate_match_id":
                        selected_candidate.id,

                    "hospital_id":
                        selected_hospital.id,

                    "hospital_name":
                        selected_hospital.name,

                    "rank":
                        selected_rank,

                    "constraint_match_score":
                        selected_score,
                },

                "signals":
                    signals,
            }
        )


    # =====================================================
    # 7. 평균 차이
    # =====================================================

    if lost_to_other_candidate > 0:

        average_rank_gap = round(
            total_rank_gap
            / lost_to_other_candidate,
            2,
        )


        average_score_gap = round(
            total_score_gap
            / lost_to_other_candidate,
            2,
        )

    else:

        average_rank_gap = 0.0

        average_score_gap = 0.0


    # =====================================================
    # 8. Signal rates
    #
    # 분모는 "다른 후보가 실제 선택된 loss case"
    # =====================================================

    signal_rates = {}


    for (
        signal,
        count,
    ) in signal_counts.items():

        signal_rates[
            signal
        ] = percentage(
            count,
            lost_to_other_candidate,
        )


    # =====================================================
    # 9. Response
    # =====================================================

    return {

        "hospital": {

            "hospital_id":
                hospital.id,

            "hospital_name":
                hospital.name,

            "district":
                hospital.district,
        },


        "decision_summary": {

            "shown_intents":
                shown_intents,

            "decision_opportunities":
                decision_opportunities,

            "selected_by_this_hospital":
                selected_by_this_hospital,

            "lost_to_other_candidate":
                lost_to_other_candidate,

            "no_selection_after_exposure":
                no_selection_after_exposure,

            "decision_win_rate_pct":
                percentage(
                    selected_by_this_hospital,
                    decision_opportunities,
                ),
        },


        "loss_signal_counts":
            signal_counts,


        "loss_signal_rates_pct":
            signal_rates,


        "comparison": {

            "average_rank_gap_on_losses":
                average_rank_gap,

            "average_score_gap_on_losses":
                average_score_gap,
        },


        "lost_cases":
            lost_cases,


        "note": (
            "Loss signals are observed differences at the "
            "time another candidate was selected. "
            "They do not prove causal reasons for user choice."
        ),
    }