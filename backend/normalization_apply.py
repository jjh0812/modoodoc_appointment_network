from datetime import datetime

from app.database import SessionLocal

from app.models import (
    ProviderOffer,
    RawOfferEvidence,
)

from app.services.offer_apply_service import (
    apply_reconciliation_decisions,
)

from app.services.offer_reconciliation_service import (
    reconcile_offer_evidence,
)


# =========================================================
# Synthetic test 기준 시각
# =========================================================

REFERENCE_TIME = datetime(
    2026,
    8,
    20,
    12,
    0,
    0,
)


# =========================================================
# DB
# =========================================================

db = SessionLocal()


try:

    # =====================================================
    # 1. RAW Evidence 읽기
    # =====================================================

    evidences = (
        db.query(
            RawOfferEvidence
        )
        .order_by(
            RawOfferEvidence.id
        )
        .all()
    )


    # =====================================================
    # 2. Reconciliation
    # =====================================================

    decisions = (
        reconcile_offer_evidence(
            evidences=evidences,
            reference_time=REFERENCE_TIME,
        )
    )


    # =====================================================
    # 3. 안전한 결과만 실제 ProviderOffer에 반영
    # =====================================================

    result = (
        apply_reconciliation_decisions(
            db=db,
            decisions=decisions,
        )
    )


    # =====================================================
    # 4. DB 최종 상태 확인
    # =====================================================

    canonical_count = (
        db.query(
            ProviderOffer
        )
        .count()
    )


    normalized_raw_count = (
        db.query(
            RawOfferEvidence
        )
        .filter(
            RawOfferEvidence
            .normalization_status
            == "NORMALIZED"
        )
        .count()
    )


    review_raw_count = (
        db.query(
            RawOfferEvidence
        )
        .filter(
            RawOfferEvidence
            .normalization_status
            == "REVIEW_REQUIRED"
        )
        .count()
    )


    # =====================================================
    # 출력
    # =====================================================

    print()

    print(
        "========================================"
    )

    print(
        "NORMALIZATION APPLY RESULT"
    )

    print(
        "========================================"
    )


    print(
        "CREATED OFFERS:",
        result[
            "created_offers"
        ],
    )


    print(
        "UPDATED OFFERS:",
        result[
            "updated_offers"
        ],
    )


    print(
        "REVIEW DECISIONS:",
        result[
            "review_decisions"
        ],
    )


    print(
        "NORMALIZED RAW EVIDENCE:",
        normalized_raw_count,
    )


    print(
        "REVIEW RAW EVIDENCE:",
        review_raw_count,
    )


    print(
        "CANONICAL PROVIDER OFFERS:",
        canonical_count,
    )


    # =====================================================
    # 처음 10개 Canonical Offer 출력
    # =====================================================

    print()

    print(
        "FIRST 10 CANONICAL OFFERS:"
    )


    offers = (
        db.query(
            ProviderOffer
        )
        .order_by(
            ProviderOffer.id
        )
        .limit(10)
        .all()
    )


    for offer in offers:

        print(
            "----------------------------------------"
        )

        print(
            "OFFER:",
            offer.id,
        )

        print(
            "PROVIDER:",
            offer.provider_id,
        )

        print(
            "RAW EVIDENCE:",
            offer.raw_evidence_id,
        )

        print(
            "PROCEDURE:",
            offer.procedure_code,
        )

        print(
            "PRICE:",
            offer.price_min,
            "~",
            offer.price_max,
        )

        print(
            "CONFIDENCE:",
            round(
                offer.confidence,
                2,
            ),
        )

        print(
            "STATUS:",
            offer.normalization_status,
        )


finally:

    db.close()