from datetime import (
    date,
    datetime,
    time,
    timedelta,
)

from sqlalchemy.orm import Session

from app.models import (
    AppointmentSlot,
    CandidateMatch,
    DecisionEvent,
    Hospital,
    PatientIntent,
    Provider,
    ProviderOffer,
)

from app.services.hold_service import (
    release_expired_hold,
)

from app.services.intent_normalization_service import (
    normalize_district,
)


# =========================================================
# 가격 표시 helper
# =========================================================

def format_price(
    value: int | None,
):

    if value is None:
        return "미확인"

    return (
        f"{value // 10_000}만원"
    )


# =========================================================
# 원하는 시간대 → 실제 datetime 범위
# =========================================================

def get_time_window(
    preferred_date: date,
    time_window: str,
):

    day_start = datetime.combine(
        preferred_date,
        time.min,
    )


    if time_window == "MORNING":

        start = (
            day_start
            + timedelta(hours=6)
        )

        end = (
            day_start
            + timedelta(hours=12)
        )


    elif time_window == "AFTERNOON":

        start = (
            day_start
            + timedelta(hours=12)
        )

        end = (
            day_start
            + timedelta(hours=18)
        )


    elif time_window == "EVENING":

        start = (
            day_start
            + timedelta(hours=18)
        )

        end = (
            day_start
            + timedelta(days=1)
        )


    elif time_window == "ANY":

        start = day_start

        end = (
            day_start
            + timedelta(days=1)
        )


    else:

        raise ValueError(
            f"Unsupported time window: {time_window}"
        )


    return (
        start,
        end,
    )


# =========================================================
# Budget 판정
# =========================================================

def evaluate_budget(
    price_min: int | None,
    price_max: int | None,
    budget_max: int | None,
):

    # -----------------------------------------------------
    # 사용자가 예산을 지정하지 않음
    # -----------------------------------------------------

    if budget_max is None:

        return (
            "NOT_SPECIFIED",
            15,
            "예산 제한이 지정되지 않았습니다.",
        )


    # -----------------------------------------------------
    # 최소가격도 모르면 자동 matching에서 제외
    # -----------------------------------------------------

    if price_min is None:

        return (
            "UNKNOWN",
            0,
            "가격 확인이 필요합니다.",
        )


    # -----------------------------------------------------
    # 시작 가격부터 예산 초과
    # -----------------------------------------------------

    if price_min > budget_max:

        return (
            "OVER_BUDGET",
            0,
            (
                f"시작 가격 {format_price(price_min)}이 "
                f"예산 {format_price(budget_max)}을 초과합니다."
            ),
        )


    # -----------------------------------------------------
    # 가격 전체 범위가 예산 안
    # -----------------------------------------------------

    if (
        price_max is not None
        and price_max <= budget_max
    ):

        return (
            "WITHIN_BUDGET",
            25,
            (
                f"예상 가격 "
                f"{format_price(price_min)}"
                f"~{format_price(price_max)}가 "
                f"예산 {format_price(budget_max)} 이내입니다."
            ),
        )


    # -----------------------------------------------------
    # 최소가격은 예산 안이지만
    # 상단 가격은 확인되지 않음
    # -----------------------------------------------------

    if price_max is None:

        return (
            "PARTIAL_MATCH",
            18,
            (
                f"시작 가격 {format_price(price_min)}은 "
                f"예산 이내지만 "
                f"상단 가격은 확인이 필요합니다."
            ),
        )


    # -----------------------------------------------------
    # 최소 가격은 예산 안
    # 최대 가격은 예산 초과 가능
    # -----------------------------------------------------

    return (
        "PARTIAL_MATCH",
        18,
        (
            f"시작 가격 {format_price(price_min)}은 "
            f"예산 이내지만 "
            f"상단 가격 {format_price(price_max)}은 "
            f"예산을 초과할 수 있습니다."
        ),
    )


# =========================================================
# 실제 Care Option Search
# =========================================================

def search_care_options(
    db: Session,
    procedure_code: str,
    district: str | None,
    preferred_date: date,
    time_window: str,
    budget_max: int | None,
    source: str,
    raw_query: str | None,
    limit: int = 3,
):

    # =====================================================
    # 0. Patient Intent Normalization
    #
    # 사용자가 말하는 지역 표현과
    # DB의 canonical 지역 표현을 통일한다.
    #
    # 예:
    #
    # 강남
    # 강남역
    # 역삼
    #
    # ↓
    #
    # 강남구
    # =====================================================

    canonical_district = (
        normalize_district(
            district
        )
    )


    # =====================================================
    # 1. Patient Intent 저장
    #
    # 중요:
    #
    # raw_query에는 사용자의 원문을 보존하고
    #
    # district에는 정규화된 canonical 값을 저장한다.
    #
    # 예:
    #
    # raw_query:
    # "강남에서 스마일 검사..."
    #
    # district:
    # "강남구"
    # =====================================================

    intent = PatientIntent(

        procedure_code=
            procedure_code,

        region="서울",

        district=
            canonical_district,

        preferred_date=
            preferred_date,

        time_window=
            time_window,

        budget_max=
            budget_max,

        source=
            source,

        raw_query=
            raw_query,
    )


    db.add(
        intent
    )


    # id를 먼저 얻기 위해 flush
    db.flush()


    # =====================================================
    # 2. 시간 조건 계산
    # =====================================================

    (
        window_start,
        window_end,
    ) = get_time_window(

        preferred_date=
            preferred_date,

        time_window=
            time_window,
    )


    # =====================================================
    # 3. Canonical ProviderOffer 조회
    #
    # REVIEW_REQUIRED RAW 데이터는
    # ProviderOffer에 들어오지 않았기 때문에
    # 자동으로 검색 대상에서 제외된다.
    # =====================================================

    query = (

        db.query(
            ProviderOffer
        )

        .join(
            Provider,
            ProviderOffer.provider_id
            == Provider.id,
        )

        .join(
            Hospital,
            Provider.hospital_id
            == Hospital.id,
        )

        .filter(
            ProviderOffer.procedure_code
            == procedure_code,

            ProviderOffer.bookable
            .is_(True),

            ProviderOffer.normalization_status
            .in_(
                [
                    "AUTO_NORMALIZED",
                    "VERIFIED",
                ]
            ),
        )
    )


    # -----------------------------------------------------
    # 지역 조건
    #
    # 기존:
    #
    # 강남 == 강남구
    # → False
    #
    # 수정:
    #
    # 강남
    # ↓ normalize
    # 강남구
    #
    # 강남구 == 강남구
    # → True
    # -----------------------------------------------------

    if canonical_district:

        query = query.filter(
            Hospital.district
            == canonical_district
        )


    offers = (
        query.all()
    )


    # =====================================================
    # 4. 만료된 HOLD 정리
    #
    # Search에서도 실제 availability를 사용해야 하므로
    # 오래된 HELD 슬롯을 먼저 정리한다.
    # =====================================================

    provider_ids = [

        offer.provider_id

        for offer in offers
    ]


    if provider_ids:

        held_slots = (

            db.query(
                AppointmentSlot
            )

            .filter(
                AppointmentSlot.provider_id
                .in_(provider_ids),

                AppointmentSlot.status
                == "HELD",

                AppointmentSlot.start_time
                >= window_start,

                AppointmentSlot.start_time
                < window_end,
            )

            .all()
        )


        for slot in held_slots:

            release_expired_hold(
                slot=slot,
                db=db,
            )


    # =====================================================
    # 5. Offer별 Constraint Match
    # =====================================================

    possible_candidates = []


    for offer in offers:

        provider = (
            offer.provider
        )

        hospital = (
            provider.hospital
        )


        # -------------------------------------------------
        # 실제 AVAILABLE 슬롯 중
        # 사용자가 요청한 시간대에서 가장 빠른 슬롯
        # -------------------------------------------------

        earliest_slot = (

            db.query(
                AppointmentSlot
            )

            .filter(
                AppointmentSlot.provider_id
                == provider.id,

                AppointmentSlot.status
                == "AVAILABLE",

                AppointmentSlot.start_time
                >= window_start,

                AppointmentSlot.start_time
                < window_end,
            )

            .order_by(
                AppointmentSlot.start_time
            )

            .first()
        )


        # -------------------------------------------------
        # 예약 가능한 시간이 없으면
        # executable candidate가 아니므로 제외
        # -------------------------------------------------

        if earliest_slot is None:

            continue


        # -------------------------------------------------
        # 예산 판정
        # -------------------------------------------------

        (
            budget_status,
            budget_points,
            budget_reason,
        ) = evaluate_budget(

            price_min=
                offer.price_min,

            price_max=
                offer.price_max,

            budget_max=
                budget_max,
        )


        # -------------------------------------------------
        # 최소가격부터 예산을 넘는 후보는 제외
        # -------------------------------------------------

        if (
            budget_status
            == "OVER_BUDGET"
        ):

            continue


        # -------------------------------------------------
        # Constraint Match Score
        #
        # 절대로 의료 품질 점수가 아니다.
        #
        # Procedure      20
        # District       20
        # Availability   25
        # Budget         25
        # Data Quality   10
        #
        # 최대 100
        # -------------------------------------------------

        score = 0.0


        # canonical procedure exact match
        score += 20


        # -------------------------------------------------
        # 지역
        #
        # query 단계에서 canonical district로 이미
        # filtering했기 때문에 여기까지 왔다면 일치
        # -------------------------------------------------

        if canonical_district:

            score += 20

        else:

            # 지역 제한이 없는 검색도
            # 불이익을 주지 않는다.
            score += 20


        # 실제 availability 존재
        score += 25


        # budget
        score += (
            budget_points
        )


        # normalization data confidence
        score += (
            offer.confidence
            * 10
        )


        score = round(
            score,
            2,
        )


        # -------------------------------------------------
        # 사용자가 이해할 수 있는 후보 선정 이유
        # -------------------------------------------------

        reasons = []


        if canonical_district:

            reasons.append(
                f"{hospital.district} 지역 조건 일치"
            )


        reasons.append(
            budget_reason
        )


        reasons.append(
            (
                f"{preferred_date.month}월 "
                f"{preferred_date.day}일 "
                f"{earliest_slot.start_time:%H:%M} "
                f"예약 가능"
            )
        )


        reasons.append(
            (
                "정규화 데이터 신뢰도 "
                f"{offer.confidence:.2f}"
            )
        )


        # -------------------------------------------------
        # CandidateMatch에 남길 설명 데이터
        # -------------------------------------------------

        explanation = {

            "requested_district":
                district,

            "canonical_district":
                canonical_district,

            "hospital_district":
                hospital.district,

            "district_match":
                (
                    canonical_district is None
                    or
                    hospital.district
                    == canonical_district
                ),

            "budget_status":
                budget_status,

            "availability_status":
                "AVAILABLE",

            "earliest_slot_time":
                earliest_slot
                .start_time
                .isoformat(),

            "offer_confidence":
                offer.confidence,

            "reasons":
                reasons,
        }


        possible_candidates.append(
            {
                "provider":
                    provider,

                "hospital":
                    hospital,

                "offer":
                    offer,

                "earliest_slot":
                    earliest_slot,

                "score":
                    score,

                "budget_status":
                    budget_status,

                "reasons":
                    reasons,

                "explanation":
                    explanation,
            }
        )


    # =====================================================
    # 6. Ranking
    #
    # 1. 높은 constraint score
    # 2. 빠른 availability
    # 3. 낮은 starting price
    # =====================================================

    possible_candidates.sort(
        key=lambda item: (

            -item["score"],

            item[
                "earliest_slot"
            ].start_time,

            (
                item[
                    "offer"
                ].price_min

                if item[
                    "offer"
                ].price_min
                is not None

                else 10**12
            ),
        )
    )


    # =====================================================
    # 7. 병원 다양성 확보
    #
    # Top 3가 같은 병원 의사만으로
    # 가득 차는 것을 우선 방지한다.
    #
    # 가능한 경우 병원당 1명씩 먼저 선택
    # =====================================================

    selected = []

    used_hospital_ids = set()


    for item in possible_candidates:

        hospital_id = (
            item[
                "hospital"
            ].id
        )


        if (
            hospital_id
            in used_hospital_ids
        ):

            continue


        selected.append(
            item
        )


        used_hospital_ids.add(
            hospital_id
        )


        if len(selected) >= limit:

            break


    # -----------------------------------------------------
    # 서로 다른 병원이 부족한 경우
    # 남은 좋은 provider로 채운다.
    # -----------------------------------------------------

    if len(selected) < limit:

        selected_provider_ids = {

            item["provider"].id

            for item in selected
        }


        for item in possible_candidates:

            if (
                item["provider"].id
                in selected_provider_ids
            ):

                continue


            selected.append(
                item
            )


            if len(selected) >= limit:

                break


    # =====================================================
    # 8. CandidateMatch + SHOWN Event 저장
    # =====================================================

    response_candidates = []


    for rank, item in enumerate(
        selected,
        start=1,
    ):

        provider = (
            item["provider"]
        )

        hospital = (
            item["hospital"]
        )

        offer = (
            item["offer"]
        )

        earliest_slot = (
            item["earliest_slot"]
        )


        candidate_match = CandidateMatch(

            intent_id=
                intent.id,

            provider_id=
                provider.id,

            offer_id=
                offer.id,

            earliest_slot_id=
                earliest_slot.id,

            match_score=
                item["score"],

            rank=
                rank,

            explanation_json=
                item["explanation"],
        )


        db.add(
            candidate_match
        )

        db.flush()


        # -----------------------------------------------
        # 실제로 이 candidate를 사용자에게
        # 보여줬다는 Decision Event
        # -----------------------------------------------

        shown_event = DecisionEvent(

            intent_id=
                intent.id,

            candidate_match_id=
                candidate_match.id,

            event_type=
                "SHOWN",

            slot_id=
                earliest_slot.id,

            event_metadata={

                "rank":
                    rank,

                "constraint_match_score":
                    item["score"],

                "requested_district":
                    district,

                "canonical_district":
                    canonical_district,
            },
        )


        db.add(
            shown_event
        )


        # -----------------------------------------------
        # API 응답용 candidate
        # -----------------------------------------------

        response_candidates.append(
            {
                "candidate_match_id":
                    candidate_match.id,

                "provider_id":
                    provider.id,

                "provider_name":
                    provider.name,

                "hospital_id":
                    hospital.id,

                "hospital_name":
                    hospital.name,

                "district":
                    hospital.district,

                "offer_id":
                    offer.id,

                "procedure_code":
                    offer.procedure_code,

                "procedure_name":
                    offer.procedure_name,

                "price_min":
                    offer.price_min,

                "price_max":
                    offer.price_max,

                "earliest_slot_id":
                    earliest_slot.id,

                "earliest_slot_time":
                    earliest_slot.start_time,

                "constraint_match_score":
                    item["score"],

                "budget_status":
                    item[
                        "budget_status"
                    ],

                "data_confidence":
                    offer.confidence,

                "reasons":
                    item["reasons"],
            }
        )


    # =====================================================
    # 9. 마지막에 한 번만 COMMIT
    #
    # PatientIntent
    # CandidateMatch
    # SHOWN DecisionEvent
    #
    # 를 하나의 transaction으로 저장
    # =====================================================

    db.commit()


    return {

        "intent_id":
            intent.id,

        "candidates":
            response_candidates,
    }