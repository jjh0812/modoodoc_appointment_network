from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    DecisionEvent,
    PatientIntent,
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
# Decision Funnel Analytics
#
# 중요한 점:
#
# SHOWN은 후보 3개를 보여주면
# event가 3개 생길 수 있다.
#
# 따라서 funnel에서는
# event 개수가 아니라
# "몇 개의 Intent가 해당 단계까지 갔는지"
# DISTINCT intent_id를 사용한다.
# =========================================================

def get_decision_funnel(
    db: Session,
) -> dict:

    # =====================================================
    # 1. 전체 Patient Intent
    #
    # 검색을 몇 번 했는가
    # =====================================================

    searched = (
        db.query(
            func.count(
                PatientIntent.id
            )
        )
        .scalar()
        or 0
    )


    # =====================================================
    # 2. DecisionEvent별
    #
    # - 실제 event 개수
    # - unique intent 개수
    #
    # 둘 다 집계
    # =====================================================

    event_rows = (
        db.query(

            DecisionEvent.event_type,

            func.count(
                DecisionEvent.id
            ).label(
                "event_count"
            ),

            func.count(
                func.distinct(
                    DecisionEvent.intent_id
                )
            ).label(
                "intent_count"
            ),
        )
        .group_by(
            DecisionEvent.event_type
        )
        .all()
    )


    # =====================================================
    # 3. Event Map
    # =====================================================

    event_map = {}


    for (
        event_type,
        event_count,
        intent_count,
    ) in event_rows:

        event_map[
            event_type
        ] = {

            "event_count":
                int(
                    event_count
                ),

            "intent_count":
                int(
                    intent_count
                ),
        }


    # =====================================================
    # 4. Funnel Stage
    #
    # Funnel에서는 unique intent 기준
    # =====================================================

    shown = (
        event_map
        .get(
            "SHOWN",
            {},
        )
        .get(
            "intent_count",
            0,
        )
    )


    selected = (
        event_map
        .get(
            "SELECTED",
            {},
        )
        .get(
            "intent_count",
            0,
        )
    )


    held = (
        event_map
        .get(
            "HELD",
            {},
        )
        .get(
            "intent_count",
            0,
        )
    )


    confirmed = (
        event_map
        .get(
            "CONFIRMED",
            {},
        )
        .get(
            "intent_count",
            0,
        )
    )


    # =====================================================
    # 5. 실제 event volume
    #
    # 예:
    #
    # 검색 Intent 1개
    # → 후보 3개 노출
    #
    # SHOWN intents = 1
    # SHOWN events  = 3
    # =====================================================

    shown_events = (
        event_map
        .get(
            "SHOWN",
            {},
        )
        .get(
            "event_count",
            0,
        )
    )


    selected_events = (
        event_map
        .get(
            "SELECTED",
            {},
        )
        .get(
            "event_count",
            0,
        )
    )


    held_events = (
        event_map
        .get(
            "HELD",
            {},
        )
        .get(
            "event_count",
            0,
        )
    )


    confirmed_events = (
        event_map
        .get(
            "CONFIRMED",
            {},
        )
        .get(
            "event_count",
            0,
        )
    )


    # =====================================================
    # 6. 검색 Source별 Intent
    #
    # 예:
    #
    # AI_SIMULATOR
    # CHATGPT_MCP
    # PUBLIC_MCP
    # =====================================================

    source_rows = (
        db.query(

            PatientIntent.source,

            func.count(
                PatientIntent.id
            ),
        )
        .group_by(
            PatientIntent.source
        )
        .order_by(
            func.count(
                PatientIntent.id
            ).desc()
        )
        .all()
    )


    by_source = {}


    for (
        source,
        count,
    ) in source_rows:

        source_name = (
            source
            or "UNKNOWN"
        )


        by_source[
            source_name
        ] = int(
            count
        )


    # =====================================================
    # 7. Response
    # =====================================================

    return {

        # -------------------------------------------------
        # 실제 funnel
        #
        # unique Patient Intent 기준
        # -------------------------------------------------

        "funnel": {

            "searched":
                searched,

            "shown":
                shown,

            "selected":
                selected,

            "held":
                held,

            "confirmed":
                confirmed,
        },


        # -------------------------------------------------
        # conversion
        # -------------------------------------------------

        "conversion_rates_pct": {

            "search_to_shown":
                percentage(
                    shown,
                    searched,
                ),

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

            "search_to_confirmed":
                percentage(
                    confirmed,
                    searched,
                ),
        },


        # -------------------------------------------------
        # raw event volume
        # -------------------------------------------------

        "event_counts": {

            "shown":
                shown_events,

            "selected":
                selected_events,

            "held":
                held_events,

            "confirmed":
                confirmed_events,
        },


        # -------------------------------------------------
        # 검색 유입 channel
        # -------------------------------------------------

        "searches_by_source":
            by_source,
    }