from datetime import datetime

from app.database import SessionLocal

from app.models import (
    ProviderOffer,
    RawOfferEvidence,
)

from app.services.offer_reconciliation_service import (
    reconcile_offer_evidence,
)


# =========================================================
# synthetic seed 기준 시각
#
# 테스트 결과가 매번 달라지지 않게
# preview에서는 고정한다.
# =========================================================

REFERENCE_TIME = datetime(
    2026,
    8,
    20,
    12,
    0,
    0,
)


db = SessionLocal()


try:

    evidences = (
        db.query(
            RawOfferEvidence
        )
        .order_by(
            RawOfferEvidence.id
        )
        .all()
    )


    decisions = (
        reconcile_offer_evidence(
            evidences=evidences,
            reference_time=REFERENCE_TIME,
        )
    )


    auto_accepted = [
        decision
        for decision in decisions
        if decision.status
        == "AUTO_ACCEPTED"
    ]


    review_required = [
        decision
        for decision in decisions
        if decision.status
        == "REVIEW_REQUIRED"
    ]


    conflicts = [
        decision
        for decision in decisions
        if decision.conflict_detected
    ]


    canonical_count = (
        db.query(
            ProviderOffer
        )
        .count()
    )


    print()

    print(
        "========================================"
    )

    print(
        "RECONCILIATION PREVIEW"
    )

    print(
        "========================================"
    )


    print(
        "RAW EVIDENCE:",
        len(evidences),
    )


    print(
        "DECISIONS:",
        len(decisions),
    )


    print(
        "AUTO ACCEPTED:",
        len(auto_accepted),
    )


    print(
        "REVIEW REQUIRED:",
        len(review_required),
    )


    print(
        "PRICE CONFLICTS:",
        len(conflicts),
    )


    print(
        "CANONICAL OFFERS IN DB:",
        canonical_count,
    )


    # =====================================================
    # AUTO ACCEPTED 처음 10개
    # =====================================================

    print()

    print(
        "FIRST 10 AUTO ACCEPTED:"
    )


    for decision in auto_accepted[:10]:

        candidate = (
            decision
            .recommended
            .candidate
        )


        print(
            "----------------------------------------"
        )

        print(
            "PROVIDER:",
            decision.provider_id,
        )

        print(
            "EVIDENCE:",
            candidate.evidence_id,
        )

        print(
            "SOURCE:",
            candidate.source_type,
        )

        print(
            "CANONICAL:",
            candidate.procedure_code,
        )

        print(
            "PRICE:",
            candidate.price_min,
            "~",
            candidate.price_max,
        )

        print(
            "EXTRACTION CONFIDENCE:",
            round(
                candidate.confidence,
                2,
            ),
        )

        print(
            "RECONCILIATION SCORE:",
            round(
                decision
                .recommended
                .total_score,
                3,
            ),
        )

        print(
            "WARNINGS:",
            decision.warnings,
        )


    # =====================================================
    # REVIEW REQUIRED
    # =====================================================

    print()

    print(
        "REVIEW REQUIRED:"
    )


    for decision in review_required:

        print(
            "----------------------------------------"
        )

        print(
            "PROVIDER:",
            decision.provider_id,
        )

        print(
            "PROCEDURE:",
            decision.procedure_code,
        )

        print(
            "REASONS:",
            decision.review_reasons,
        )


        if decision.recommended:

            candidate = (
                decision
                .recommended
                .candidate
            )


            print(
                "RECOMMENDED EVIDENCE:",
                candidate.evidence_id,
            )

            print(
                "RECOMMENDED SOURCE:",
                candidate.source_type,
            )

            print(
                "PRICE:",
                candidate.price_min,
                "~",
                candidate.price_max,
            )

            print(
                "SCORE:",
                round(
                    decision
                    .recommended
                    .total_score,
                    3,
                ),
            )


        # -----------------------------------------------
        # 여러 source가 있으면 전부 비교해서 보여준다.
        # -----------------------------------------------

        if (
            len(
                decision.candidates
            )
            > 1
        ):

            print(
                "ALL SOURCES:"
            )


            for scored in (
                decision.candidates
            ):

                candidate = (
                    scored.candidate
                )


                print(
                    "  -",
                    "Evidence",
                    candidate.evidence_id,
                    "|",
                    candidate.source_type,
                    "|",
                    candidate.price_min,
                    "~",
                    candidate.price_max,
                    "| score",
                    round(
                        scored.total_score,
                        3,
                    ),
                    "| age",
                    scored.age_days,
                    "days",
                )


finally:

    db.close()