from collections import defaultdict

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
# Hospital Decision Analytics
#
# 핵심 질문:
#
# AI가 어떤 병원을 보여줬는가?
#       ↓
# 사용자가 무엇을 선택했는가?
#       ↓
# 어떤 병원이 HOLD 되었는가?
#       ↓
# 실제 예약까지 갔는가?
#
#
# funnel 계산은 단순 event 개수보다
# unique intent 기준을 우선 사용한다.
# =========================================================

def get_hospital_decision_analytics(
    db: Session,
) -> dict:

    # =====================================================
    # 1. Transaction Graph 조회
    #
    # DecisionEvent
    #     ↓
    # CandidateMatch
    #     ↓
    # Provider
    #     ↓
    # Hospital
    # =====================================================

    rows = (
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
        .order_by(
            DecisionEvent.id.asc()
        )
        .all()
    )


    # =====================================================
    # 2. 병원별 임시 집계 공간
    # =====================================================

    hospital_map = {}


    for (
        event,
        candidate,
        provider,
        hospital,
    ) in rows:

        if hospital.id not in hospital_map:

            hospital_map[hospital.id] = {

                "hospital_id":
                    hospital.id,

                "hospital_name":
                    hospital.name,

                "district":
                    hospital.district,

                # -----------------------------------------
                # unique intent
                # -----------------------------------------

                "shown_intents":
                    set(),

                "selected_intents":
                    set(),

                "held_intents":
                    set(),

                "confirmed_intents":
                    set(),

                # -----------------------------------------
                # raw event volume
                # -----------------------------------------

                "shown_events":
                    0,

                "selected_events":
                    0,

                "held_events":
                    0,

                "confirmed_events":
                    0,

                # -----------------------------------------
                # Top-1 노출
                # -----------------------------------------

                "top1_shown_intents":
                    set(),

                # -----------------------------------------
                # 실제 노출 Rank 기록
                # -----------------------------------------

                "shown_ranks":
                    [],
            }


        stats = (
            hospital_map[
                hospital.id
            ]
        )


        event_type = (
            event.event_type
        )


        # =================================================
        # SHOWN
        # =================================================

        if event_type == "SHOWN":

            stats[
                "shown_events"
            ] += 1

            stats[
                "shown_intents"
            ].add(
                event.intent_id
            )


            if candidate.rank is not None:

                stats[
                    "shown_ranks"
                ].append(
                    candidate.rank
                )


                if candidate.rank == 1:

                    stats[
                        "top1_shown_intents"
                    ].add(
                        event.intent_id
                    )


        # =================================================
        # SELECTED
        # =================================================

        elif event_type == "SELECTED":

            stats[
                "selected_events"
            ] += 1

            stats[
                "selected_intents"
            ].add(
                event.intent_id
            )


        # =================================================
        # HELD
        # =================================================

        elif event_type == "HELD":

            stats[
                "held_events"
            ] += 1

            stats[
                "held_intents"
            ].add(
                event.intent_id
            )


        # =================================================
        # CONFIRMED
        # =================================================

        elif event_type == "CONFIRMED":

            stats[
                "confirmed_events"
            ] += 1

            stats[
                "confirmed_intents"
            ].add(
                event.intent_id
            )


    # =====================================================
    # 3. 최종 결과 생성
    # =====================================================

    hospitals = []


    for stats in hospital_map.values():

        shown = len(
            stats[
                "shown_intents"
            ]
        )

        selected = len(
            stats[
                "selected_intents"
            ]
        )

        held = len(
            stats[
                "held_intents"
            ]
        )

        confirmed = len(
            stats[
                "confirmed_intents"
            ]
        )

        top1_shown = len(
            stats[
                "top1_shown_intents"
            ]
        )


        shown_ranks = (
            stats[
                "shown_ranks"
            ]
        )


        if shown_ranks:

            average_rank = round(
                sum(
                    shown_ranks
                )
                / len(
                    shown_ranks
                ),
                2,
            )

        else:

            average_rank = None


        hospitals.append(
            {
                "hospital_id":
                    stats[
                        "hospital_id"
                    ],

                "hospital_name":
                    stats[
                        "hospital_name"
                    ],

                "district":
                    stats[
                        "district"
                    ],


                # =========================================
                # Funnel
                # =========================================

                "funnel": {

                    "shown":
                        shown,

                    "selected":
                        selected,

                    "held":
                        held,

                    "confirmed":
                        confirmed,
                },


                # =========================================
                # Conversion
                # =========================================

                "conversion_rates_pct": {

                    "shown_to_selected":
                        percentage(
                            selected,
                            shown,
                        ),

                    "selected_to_held":
                        percentage(
                            held,
                            selected,
                        ),

                    "held_to_confirmed":
                        percentage(
                            confirmed,
                            held,
                        ),

                    "shown_to_confirmed":
                        percentage(
                            confirmed,
                            shown,
                        ),
                },


                # =========================================
                # Ranking exposure
                # =========================================

                "ranking": {

                    "top1_shown":
                        top1_shown,

                    "top1_share_pct":
                        percentage(
                            top1_shown,
                            shown,
                        ),

                    "average_shown_rank":
                        average_rank,
                },


                # =========================================
                # Raw Event Count
                # =========================================

                "event_counts": {

                    "shown":
                        stats[
                            "shown_events"
                        ],

                    "selected":
                        stats[
                            "selected_events"
                        ],

                    "held":
                        stats[
                            "held_events"
                        ],

                    "confirmed":
                        stats[
                            "confirmed_events"
                        ],
                },
            }
        )


    # =====================================================
    # 4. 기본 정렬
    #
    # 우선 선택을 많이 받은 병원
    #     ↓
    # 예약 확정
    #     ↓
    # 노출
    #
    # 의료 품질 ranking이 아님.
    # =====================================================

    hospitals.sort(
        key=lambda hospital: (
            hospital[
                "funnel"
            ][
                "selected"
            ],

            hospital[
                "funnel"
            ][
                "confirmed"
            ],

            hospital[
                "funnel"
            ][
                "shown"
            ],
        ),
        reverse=True,
    )


    # =====================================================
    # 5. Response
    # =====================================================

    return {

        "hospital_count":
            len(
                hospitals
            ),

        "hospitals":
            hospitals,

        "note":
            (
                "These metrics describe prototype "
                "decision and transaction behavior. "
                "They are not medical quality scores."
            ),
    }