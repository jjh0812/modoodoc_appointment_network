from dataclasses import dataclass, field
from datetime import datetime

from app.models import RawOfferEvidence

from app.services.offer_normalization_service import (
    ExtractedOfferCandidate,
    extract_offer_candidate,
)


# =========================================================
# 1. Source 신뢰도
#
# 주의:
# 이것은 병원의 신뢰도 점수가 아니다.
#
# "이 source 형식이 현재 offer를 표현하는 데
# 얼마나 직접적이고 구조화되어 있는가?"
#
# 에 대한 prototype 정책이다.
# =========================================================

SOURCE_PRIORITY = {

    # 병원이 직접 최신 상태를 입력
    "ADMIN": 1.00,

    # 구조화된 API
    "JSON_API": 0.97,

    # 구조화된 JSON
    "NESTED_JSON": 0.95,

    # 일반 CSV
    "CSV": 0.92,

    # 일부 정보가 빠진 관리자 입력
    "ADMIN_INCOMPLETE": 0.85,

    # 홈페이지
    "WEBSITE": 0.75,

    # 오래된 형태의 CSV
    "LEGACY_CSV": 0.70,

    # 자유 텍스트
    "FREE_TEXT": 0.60,

    # 매우 빈약한 텍스트
    "SPARSE_TEXT": 0.50,
}


# =========================================================
# 2. 자동 canonicalization 기준
# =========================================================

AUTO_ACCEPT_MIN_CONFIDENCE = 0.70


# =========================================================
# 3. 가격 충돌 판단 기준
#
# 가격 차이가:
#
# 최소 100,000원 이상이고
# 동시에 5% 이상이면
#
# material conflict로 판단
# =========================================================

MIN_PRICE_CONFLICT_WON = 100_000

MIN_PRICE_CONFLICT_RATIO = 0.05


# =========================================================
# 4. 후보 하나의 reconciliation score
# =========================================================

@dataclass
class ScoredCandidate:

    candidate: ExtractedOfferCandidate

    source_priority: float

    freshness_score: float

    age_days: int | None

    total_score: float


# =========================================================
# 5. Provider 하나에 대한 최종 판단
#
# 아직 ProviderOffer DB row가 아니다.
#
# "이걸 자동 채택할 것인가?"
# 를 결정한 preview 결과다.
# =========================================================

@dataclass
class ReconciliationDecision:

    provider_id: int | None

    procedure_code: str | None

    status: str

    recommended: ScoredCandidate | None

    candidates: list[ScoredCandidate] = field(
        default_factory=list
    )

    review_reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    conflict_detected: bool = False


    @property
    def auto_accepted(self):

        return (
            self.status
            == "AUTO_ACCEPTED"
        )


# =========================================================
# 6. Freshness 계산
#
# 최근 데이터일수록 높은 점수
# =========================================================

def calculate_freshness(
    evidence: RawOfferEvidence,
    reference_time: datetime,
):

    source_time = (
        evidence.observed_at
        or evidence.received_at
    )


    if source_time is None:

        return (
            0.40,
            None,
        )


    age = (
        reference_time
        - source_time
    )


    age_days = max(
        0,
        age.days,
    )


    if age_days <= 1:

        score = 1.00

    elif age_days <= 7:

        score = 0.90

    elif age_days <= 30:

        score = 0.75

    elif age_days <= 90:

        score = 0.50

    else:

        score = 0.25


    return (
        score,
        age_days,
    )


# =========================================================
# 7. Candidate score
#
# Extraction confidence
# + Source quality
# + Freshness
#
# 를 합친다.
# =========================================================

def score_candidate(
    candidate: ExtractedOfferCandidate,
    evidence: RawOfferEvidence,
    reference_time: datetime,
):

    source_priority = (
        SOURCE_PRIORITY.get(
            candidate.source_type,
            0.40,
        )
    )


    (
        freshness_score,
        age_days,
    ) = calculate_freshness(
        evidence=evidence,
        reference_time=reference_time,
    )


    total_score = (

        candidate.confidence
        * 0.55

        +

        source_priority
        * 0.30

        +

        freshness_score
        * 0.15
    )


    return ScoredCandidate(

        candidate=candidate,

        source_priority=
            source_priority,

        freshness_score=
            freshness_score,

        age_days=
            age_days,

        total_score=
            round(
                total_score,
                4,
            ),
    )


# =========================================================
# 8. 두 가격이 실제로 충돌하는지 확인
# =========================================================

def materially_different_prices(
    value_a: int | None,
    value_b: int | None,
):

    # 둘 중 하나라도 값이 없으면
    # 여기서는 확정적인 conflict로 판단하지 않는다.

    if (
        value_a is None
        or value_b is None
    ):

        return False


    difference = abs(
        value_a
        - value_b
    )


    smaller_value = min(
        value_a,
        value_b,
    )


    if smaller_value <= 0:

        return (
            difference
            >= MIN_PRICE_CONFLICT_WON
        )


    ratio = (
        difference
        / smaller_value
    )


    return (
        difference
        >= MIN_PRICE_CONFLICT_WON

        and

        ratio
        >= MIN_PRICE_CONFLICT_RATIO
    )


# =========================================================
# 9. Candidate들 사이 가격 충돌 검사
# =========================================================

def detect_price_conflict(
    scored_candidates: list[ScoredCandidate],
):

    if len(scored_candidates) <= 1:

        return False


    for i in range(
        len(scored_candidates)
    ):

        for j in range(
            i + 1,
            len(scored_candidates),
        ):

            candidate_a = (
                scored_candidates[i]
                .candidate
            )

            candidate_b = (
                scored_candidates[j]
                .candidate
            )


            min_conflict = (
                materially_different_prices(
                    candidate_a.price_min,
                    candidate_b.price_min,
                )
            )


            max_conflict = (
                materially_different_prices(
                    candidate_a.price_max,
                    candidate_b.price_max,
                )
            )


            if (
                min_conflict
                or max_conflict
            ):

                return True


    return False


# =========================================================
# 10. RAW evidence 전체 reconciliation
# =========================================================

def reconcile_offer_evidence(
    evidences: list[RawOfferEvidence],
    reference_time: datetime | None = None,
):

    if reference_time is None:

        reference_time = (
            datetime.utcnow()
        )


    # -----------------------------------------------------
    # Evidence ID → 실제 DB evidence
    # -----------------------------------------------------

    evidence_by_id = {

        evidence.id:
            evidence

        for evidence
        in evidences
    }


    # -----------------------------------------------------
    # 정상 candidate group
    #
    # key:
    #
    # (
    #   provider_id,
    #   procedure_code
    # )
    # -----------------------------------------------------

    groups = {}


    # -----------------------------------------------------
    # Extraction 자체에서 이미 review가 필요한 것
    # -----------------------------------------------------

    unresolved_candidates = []


    # =====================================================
    # 11. 먼저 38개 전부 Extraction
    # =====================================================

    for evidence in evidences:

        candidate = (
            extract_offer_candidate(
                evidence
            )
        )


        if candidate.review_required:

            unresolved_candidates.append(
                candidate
            )

            continue


        key = (
            candidate.provider_id,
            candidate.procedure_code,
        )


        groups.setdefault(
            key,
            []
        )


        groups[key].append(
            candidate
        )


    decisions = []


    # =====================================================
    # 12. Extraction 단계에서 이미 막힌 것
    # =====================================================

    for candidate in unresolved_candidates:

        evidence = (
            evidence_by_id[
                candidate.evidence_id
            ]
        )


        scored = (
            score_candidate(
                candidate=candidate,
                evidence=evidence,
                reference_time=reference_time,
            )
        )


        decision = ReconciliationDecision(

            provider_id=
                candidate.provider_id,

            procedure_code=
                candidate.procedure_code,

            status=
                "REVIEW_REQUIRED",

            recommended=
                scored,

            candidates=[
                scored
            ],

            review_reasons=list(
                candidate.review_reasons
            ),

            warnings=list(
                candidate.warnings
            ),

            conflict_detected=False,
        )


        decisions.append(
            decision
        )


    # =====================================================
    # 13. Provider별 reconciliation
    # =====================================================

    for (
        provider_id,
        procedure_code,
    ), candidates in groups.items():

        scored_candidates = []


        # -------------------------------------------------
        # Candidate별 점수 계산
        # -------------------------------------------------

        for candidate in candidates:

            evidence = (
                evidence_by_id[
                    candidate.evidence_id
                ]
            )


            scored = (
                score_candidate(
                    candidate=candidate,
                    evidence=evidence,
                    reference_time=reference_time,
                )
            )


            scored_candidates.append(
                scored
            )


        # -------------------------------------------------
        # 점수가 가장 높은 source부터
        # -------------------------------------------------

        scored_candidates.sort(
            key=lambda item:
                item.total_score,
            reverse=True,
        )


        recommended = (
            scored_candidates[0]
        )


        review_reasons = []

        warnings = list(
            recommended
            .candidate
            .warnings
        )


        # -------------------------------------------------
        # Extraction confidence가 너무 낮으면
        # 자동 확정하지 않는다.
        # -------------------------------------------------

        if (
            recommended
            .candidate
            .confidence

            <

            AUTO_ACCEPT_MIN_CONFIDENCE
        ):

            review_reasons.append(
                "LOW_EXTRACTION_CONFIDENCE"
            )


        # -------------------------------------------------
        # 너무 오래된 source면 review
        # -------------------------------------------------

        if (
            recommended.age_days
            is not None

            and

            recommended.age_days > 90
        ):

            review_reasons.append(
                "STALE_SOURCE"
            )


        # -------------------------------------------------
        # 여러 source가 있는데
        # 가격이 실질적으로 다르면
        # 자동으로 평균내거나 덮어쓰지 않는다.
        # -------------------------------------------------

        conflict_detected = (
            detect_price_conflict(
                scored_candidates
            )
        )


        if conflict_detected:

            review_reasons.append(
                "MATERIAL_PRICE_CONFLICT"
            )


        # -------------------------------------------------
        # 여러 source가 있지만
        # 가격 충돌이 크지 않다면
        # 참고 warning만 남긴다.
        # -------------------------------------------------

        if (
            len(scored_candidates) > 1
            and not conflict_detected
        ):

            warnings.append(
                "MULTIPLE_SOURCES_CONSISTENT"
            )


        # -------------------------------------------------
        # 최종 판단
        # -------------------------------------------------

        if review_reasons:

            status = (
                "REVIEW_REQUIRED"
            )

        else:

            status = (
                "AUTO_ACCEPTED"
            )


        decision = ReconciliationDecision(

            provider_id=
                provider_id,

            procedure_code=
                procedure_code,

            status=
                status,

            recommended=
                recommended,

            candidates=
                scored_candidates,

            review_reasons=
                review_reasons,

            warnings=
                warnings,

            conflict_detected=
                conflict_detected,
        )


        decisions.append(
            decision
        )


    return decisions