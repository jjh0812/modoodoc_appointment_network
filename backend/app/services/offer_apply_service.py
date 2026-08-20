from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    ProviderOffer,
    RawOfferEvidence,
)

from app.services.offer_reconciliation_service import (
    ReconciliationDecision,
)


# =========================================================
# Reconciliation 결과를 실제 Canonical Offer에 반영
#
# 핵심 원칙:
#
# AUTO_ACCEPTED
# → ProviderOffer 생성 / 갱신
#
# REVIEW_REQUIRED
# → ProviderOffer에는 절대 넣지 않음
# =========================================================

def apply_reconciliation_decisions(
    db: Session,
    decisions: list[ReconciliationDecision],
):

    created_count = 0

    updated_count = 0

    review_decision_count = 0

    normalized_evidence_count = 0

    review_evidence_count = 0


    # =====================================================
    # Decision 하나씩 처리
    # =====================================================

    for decision in decisions:

        # -------------------------------------------------
        # 이 decision에 포함된 모든 RAW evidence
        # -------------------------------------------------

        evidence_ids = [

            scored.candidate.evidence_id

            for scored
            in decision.candidates
        ]


        evidences = (
            db.query(
                RawOfferEvidence
            )
            .filter(
                RawOfferEvidence.id.in_(
                    evidence_ids
                )
            )
            .all()
        )


        # =================================================
        # 1. REVIEW REQUIRED
        #
        # Canonical Offer 생성하지 않음
        # =================================================

        if (
            decision.status
            == "REVIEW_REQUIRED"
        ):

            review_decision_count += 1


            for evidence in evidences:

                evidence.normalization_status = (
                    "REVIEW_REQUIRED"
                )

                review_evidence_count += 1


            continue


        # =================================================
        # 2. AUTO ACCEPTED가 아니면 방어적으로 skip
        # =================================================

        if (
            decision.status
            != "AUTO_ACCEPTED"
        ):

            continue


        # =================================================
        # 3. Recommended candidate 확인
        # =================================================

        if decision.recommended is None:

            continue


        candidate = (
            decision
            .recommended
            .candidate
        )


        # -------------------------------------------------
        # provider가 없는 canonical offer는 만들 수 없음
        # -------------------------------------------------

        if candidate.provider_id is None:

            continue


        # -------------------------------------------------
        # canonical procedure가 없는 경우도 만들지 않음
        # -------------------------------------------------

        if candidate.procedure_code is None:

            continue


        # =================================================
        # 4. 기존 ProviderOffer 확인
        #
        # 같은 provider + procedure가 이미 있다면
        # 새 row를 계속 만들지 않고 갱신
        #
        # → Apply를 여러 번 실행해도 중복 방지
        # =================================================

        existing_offer = (
            db.query(
                ProviderOffer
            )
            .filter(
                ProviderOffer.provider_id
                == candidate.provider_id,

                ProviderOffer.procedure_code
                == candidate.procedure_code,
            )
            .first()
        )


        # =================================================
        # 5. 기존 offer가 없다면 생성
        # =================================================

        if existing_offer is None:

            offer = ProviderOffer(

                provider_id=
                    candidate.provider_id,

                raw_evidence_id=
                    candidate.evidence_id,

                procedure_code=
                    candidate.procedure_code,

                procedure_name=
                    candidate.procedure_name,

                price_min=
                    candidate.price_min,

                price_max=
                    candidate.price_max,

                currency=
                    candidate.currency,

                inspection_fee_included=
                    candidate.inspection_fee_included,

                conditional_discount=
                    candidate.conditional_discount,

                bookable=
                    candidate.bookable,

                confidence=
                    candidate.confidence,

                normalization_status=
                    "AUTO_NORMALIZED",

                # 사람이 검증한 것은 아니므로
                # verified_at은 아직 비워둔다.
                verified_at=None,

                created_at=
                    datetime.utcnow(),
            )


            db.add(
                offer
            )


            created_count += 1


        # =================================================
        # 6. 이미 있다면 최신 reconciliation 결과로 갱신
        # =================================================

        else:

            existing_offer.raw_evidence_id = (
                candidate.evidence_id
            )

            existing_offer.procedure_name = (
                candidate.procedure_name
            )

            existing_offer.price_min = (
                candidate.price_min
            )

            existing_offer.price_max = (
                candidate.price_max
            )

            existing_offer.currency = (
                candidate.currency
            )

            existing_offer.inspection_fee_included = (
                candidate
                .inspection_fee_included
            )

            existing_offer.conditional_discount = (
                candidate
                .conditional_discount
            )

            existing_offer.bookable = (
                candidate.bookable
            )

            existing_offer.confidence = (
                candidate.confidence
            )

            existing_offer.normalization_status = (
                "AUTO_NORMALIZED"
            )

            existing_offer.verified_at = None


            updated_count += 1


        # =================================================
        # 7. 해당 decision의 RAW evidence는
        #    normalization 처리 완료 표시
        #
        # ProviderOffer.raw_evidence_id가
        # 실제로 선택된 evidence를 가리킨다.
        # =================================================

        for evidence in evidences:

            evidence.normalization_status = (
                "NORMALIZED"
            )

            normalized_evidence_count += 1


    # =====================================================
    # 8. 모든 변경을 마지막에 한 번만 commit
    # =====================================================

    db.commit()


    return {

        "created_offers":
            created_count,

        "updated_offers":
            updated_count,

        "review_decisions":
            review_decision_count,

        "normalized_evidence":
            normalized_evidence_count,

        "review_evidence":
            review_evidence_count,
    }