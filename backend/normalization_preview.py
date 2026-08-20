from collections import Counter

from app.database import SessionLocal

from app.models import (
    ProviderOffer,
    RawOfferEvidence,
)

from app.services.offer_normalization_service import (
    extract_offer_candidate,
)


# =========================================================
# DB
# =========================================================

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


    candidates = []

    errors = []


    # =====================================================
    # 38개 RAW 모두 extraction
    # =====================================================

    for evidence in evidences:

        try:

            candidate = (
                extract_offer_candidate(
                    evidence
                )
            )

            candidates.append(
                candidate
            )


        except Exception as error:

            errors.append(
                (
                    evidence.id,
                    evidence.source_type,
                    str(error),
                )
            )


    # =====================================================
    # 집계
    # =====================================================

    source_counts = Counter(
        candidate.source_type
        for candidate in candidates
    )


    review_count = sum(
        1
        for candidate in candidates
        if candidate.review_required
    )


    warning_count = sum(
        1
        for candidate in candidates
        if candidate.warnings
    )


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
        "NORMALIZATION EXTRACTION PREVIEW"
    )

    print(
        "========================================"
    )


    print(
        "RAW EVIDENCE:",
        len(evidences),
    )


    print(
        "EXTRACTED:",
        len(candidates),
    )


    print(
        "ERRORS:",
        len(errors),
    )


    print(
        "REVIEW REQUIRED:",
        review_count,
    )


    print(
        "WITH WARNINGS:",
        warning_count,
    )


    print(
        "CANONICAL OFFERS IN DB:",
        canonical_count,
    )


    print()

    print(
        "SOURCE BREAKDOWN:"
    )


    for source_type, count in sorted(
        source_counts.items()
    ):

        print(
            f"  {source_type}: {count}"
        )


    # =====================================================
    # 처음 12개 예시
    # =====================================================

    print()

    print(
        "FIRST 12 EXTRACTIONS:"
    )


    for candidate in candidates[:12]:

        print(
            "----------------------------------------"
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
            "PROVIDER:",
            candidate.provider_id,
        )

        print(
            "RAW PROCEDURE:",
            candidate.procedure_text,
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
            "CONFIDENCE:",
            candidate.confidence,
        )

        print(
            "REVIEW:",
            candidate.review_reasons,
        )

        print(
            "WARNINGS:",
            candidate.warnings,
        )


    # =====================================================
    # REVIEW REQUIRED만 별도 출력
    # =====================================================

    print()

    print(
        "REVIEW REQUIRED ITEMS:"
    )


    for candidate in candidates:

        if candidate.review_required:

            print(
                "EVIDENCE:",
                candidate.evidence_id,
                "| PROVIDER:",
                candidate.provider_id,
                "| SOURCE:",
                candidate.source_type,
                "| REASONS:",
                candidate.review_reasons,
            )


    # =====================================================
    # Parser 자체 오류
    # =====================================================

    if errors:

        print()

        print(
            "EXTRACTION ERRORS:"
        )


        for error in errors:

            print(
                error
            )


finally:

    db.close()