import csv
import hashlib
import io
import json

from datetime import (
    datetime,
    timedelta,
)

from app.database import SessionLocal

from app.models import (
    Appointment,
    AppointmentSlot,
    Hospital,
    Provider,
    ProviderOffer,
    RawOfferEvidence,
    SlotHold,
)


# =========================================================
# 1. 기본 설정
# =========================================================

BASE_DATE = datetime(
    2026,
    8,
    22,
    9,
    0,
    0,
)


# =========================================================
# 2. SHA-256
#
# 같은 RAW 데이터가 다시 들어왔는지,
# 원본이 바뀌었는지 식별하기 위한 fingerprint
# =========================================================

def make_hash(
    payload: str,
):

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


# =========================================================
# 3. RAW Evidence 저장 helper
# =========================================================

def add_raw_evidence(
    db,
    hospital_id,
    provider_id,
    source_type,
    source_reference,
    raw_payload,
    observed_at,
):

    evidence = RawOfferEvidence(
        hospital_id=hospital_id,
        provider_id=provider_id,
        source_type=source_type,
        source_reference=source_reference,
        raw_payload=raw_payload,
        content_hash=make_hash(
            raw_payload
        ),
        observed_at=observed_at,
        normalization_status="RECEIVED",
    )

    db.add(
        evidence
    )


# =========================================================
# 4. 가상 병원 설정
#
# 모두 fictional data
# =========================================================

HOSPITALS = [

    {
        "name": "모두비전강남안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "강남역 인근",
        "doctor_count": 4,
        "source_style": "JSON_API",
    },

    {
        "name": "모두아이역삼안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "역삼역 인근",
        "doctor_count": 3,
        "source_style": "CSV",
    },

    {
        "name": "모두클리어신사안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "신사역 인근",
        "doctor_count": 4,
        "source_style": "FREE_TEXT",
    },

    {
        "name": "모두서울서초안과 (가상)",
        "region": "서울",
        "district": "서초구",
        "address_label": "교대역 인근",
        "doctor_count": 3,
        "source_style": "ADMIN",
    },

    {
        "name": "모두밝은잠실안과 (가상)",
        "region": "서울",
        "district": "송파구",
        "address_label": "잠실역 인근",
        "doctor_count": 4,
        "source_style": "WEBSITE",
    },

    {
        "name": "모두포커스삼성안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "삼성역 인근",
        "doctor_count": 3,
        "source_style": "NESTED_JSON",
    },

    {
        "name": "모두렌즈논현안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "논현역 인근",
        "doctor_count": 4,
        "source_style": "LEGACY_CSV",
    },

    {
        "name": "모두스마일청담안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "청담역 인근",
        "doctor_count": 3,
        "source_style": "SPARSE_TEXT",
    },

    {
        "name": "모두뷰서초안과 (가상)",
        "region": "서울",
        "district": "서초구",
        "address_label": "서초역 인근",
        "doctor_count": 3,
        "source_style": "ADMIN_INCOMPLETE",
    },

    {
        "name": "모두프라임강남안과 (가상)",
        "region": "서울",
        "district": "강남구",
        "address_label": "강남대로 인근",
        "doctor_count": 3,
        "source_style": "CONFLICTING",
    },
]


# =========================================================
# 5. 시술명도 일부러 제각각
#
# 결국 Normalizer가 같은 canonical concept로
# 매핑해야 한다.
# =========================================================

PROCEDURE_ALIASES = [

    "스마일라식",
    "SMILE",
    "스마일 프로",
    "시력교정 스마일",
    "SMILE LASIK",
    "스마일 시력교정",
]


# =========================================================
# 6. 가격도 병원/의사마다 다르게 생성
# =========================================================

PRICE_BASES = [

    1_590_000,
    1_690_000,
    1_790_000,
    1_890_000,
    1_990_000,
    2_090_000,
    2_190_000,
    2_290_000,
]


# =========================================================
# 7. 병원별 RAW payload 생성
#
# 핵심:
#
# 같은 의미의 offer인데도
# 병원마다 전혀 다른 모양으로 들어온다.
# =========================================================

def build_raw_payload(
    source_style,
    hospital_name,
    provider_name,
    procedure_text,
    price_min,
    price_max,
):

    # -----------------------------------------------------
    # A. 깔끔한 JSON API
    # -----------------------------------------------------

    if source_style == "JSON_API":

        return json.dumps(
            {
                "doctor": provider_name,
                "service": procedure_text,
                "price": {
                    "min": price_min,
                    "max": price_max,
                    "currency": "KRW",
                },
                "exam_fee_included": True,
                "bookable": True,
            },
            ensure_ascii=False,
        )


    # -----------------------------------------------------
    # B. CSV
    # -----------------------------------------------------

    if source_style == "CSV":

        output = io.StringIO()

        writer = csv.writer(
            output
        )

        writer.writerow(
            [
                "doctor_name",
                "treatment",
                "min_price",
                "max_price",
                "memo",
            ]
        )

        writer.writerow(
            [
                provider_name,
                procedure_text,
                price_min,
                price_max,
                "검사비 포함",
            ]
        )

        return output.getvalue()


    # -----------------------------------------------------
    # C. 자유 텍스트
    # -----------------------------------------------------

    if source_style == "FREE_TEXT":

        min_manwon = (
            price_min // 10_000
        )

        return (
            f"{provider_name} 원장 "
            f"{procedure_text} {min_manwon}만원부터. "
            f"검사비 별도. "
            f"당일 수술 결정 시 추가 할인 가능."
        )


    # -----------------------------------------------------
    # D. 병원 관리자 직접 입력
    # -----------------------------------------------------

    if source_style == "ADMIN":

        return (
            f"PROVIDER={provider_name}\n"
            f"ITEM={procedure_text}\n"
            f"PRICE_MIN={price_min}\n"
            f"PRICE_MAX={price_max}\n"
            f"INSPECTION_INCLUDED=Y\n"
            f"BOOKABLE=Y"
        )


    # -----------------------------------------------------
    # E. 홈페이지 문구
    # -----------------------------------------------------

    if source_style == "WEBSITE":

        min_manwon = (
            price_min // 10_000
        )

        max_manwon = (
            price_max // 10_000
        )

        return (
            f"<div class='vision-event'>"
            f"<h3>{procedure_text}</h3>"
            f"<p>{provider_name} 원장</p>"
            f"<strong>"
            f"{min_manwon}~{max_manwon}만원"
            f"</strong>"
            f"<small>"
            f"개인 눈 상태에 따라 비용이 달라질 수 있습니다."
            f"</small>"
            f"</div>"
        )


    # -----------------------------------------------------
    # F. 중첩 JSON
    # -----------------------------------------------------

    if source_style == "NESTED_JSON":

        return json.dumps(
            {
                "clinic": {
                    "name": hospital_name,
                },
                "staff": {
                    "doctor": {
                        "display_name":
                            provider_name,
                    }
                },
                "products": [
                    {
                        "category":
                            "vision",
                        "display":
                            procedure_text,
                        "pricing": {
                            "from":
                                price_min,
                            "to":
                                price_max,
                        },
                    }
                ],
            },
            ensure_ascii=False,
        )


    # -----------------------------------------------------
    # G. 오래된 형태의 CSV
    #
    # column 이름조차 표준적이지 않음
    # -----------------------------------------------------

    if source_style == "LEGACY_CSV":

        return (
            "DR,NM,LOW,HIGH,ETC\n"
            f"{provider_name},"
            f"{procedure_text},"
            f"{price_min},"
            f"{price_max},"
            f"VAT포함"
        )


    # -----------------------------------------------------
    # H. 정보가 매우 부족한 자유 텍스트
    # -----------------------------------------------------

    if source_style == "SPARSE_TEXT":

        min_manwon = (
            price_min // 10_000
        )

        return (
            f"{procedure_text} "
            f"{min_manwon}만원~ "
            f"/ 의료진 지정시 비용 상이"
        )


    # -----------------------------------------------------
    # I. 관리자 데이터이지만 일부 정보 없음
    #
    # max price가 없음
    # -----------------------------------------------------

    if source_style == "ADMIN_INCOMPLETE":

        return json.dumps(
            {
                "provider_name":
                    provider_name,

                "procedure":
                    procedure_text,

                "starting_price":
                    price_min,

                "note":
                    "최종 비용 상담 후 확정",
            },
            ensure_ascii=False,
        )


    raise ValueError(
        f"Unknown source style: {source_style}"
    )


# =========================================================
# 8. 테스트 DB seed
# =========================================================

def seed_market():

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # 기존 개발용 transaction / market 데이터 삭제
        #
        # FK 때문에 자식 → 부모 순서
        # -------------------------------------------------

        db.query(
            Appointment
        ).delete()

        db.query(
            SlotHold
        ).delete()

        db.query(
            AppointmentSlot
        ).delete()

        db.query(
            ProviderOffer
        ).delete()

        db.query(
            RawOfferEvidence
        ).delete()

        db.query(
            Provider
        ).delete()

        db.query(
            Hospital
        ).delete()

        db.commit()


        provider_counter = 0


        # =================================================
        # 병원 생성
        # =================================================

        for hospital_index, config in enumerate(
            HOSPITALS,
            start=1,
        ):

            hospital = Hospital(
                name=config["name"],
                region=config["region"],
                district=config["district"],
                address_label=config[
                    "address_label"
                ],
            )

            db.add(
                hospital
            )

            db.flush()


            # =============================================
            # 병원 안 의사 생성
            # =============================================

            for doctor_index in range(
                1,
                config["doctor_count"] + 1,
            ):

                provider_counter += 1


                provider = Provider(
                    hospital_id=hospital.id,
                    name=(
                        f"가상의사 "
                        f"{provider_counter:02d}"
                    ),
                    specialty="안과 / 시력교정",
                )

                db.add(
                    provider
                )

                db.flush()


                # =========================================
                # 의사별 서로 다른 procedure 표현
                # =========================================

                procedure_text = (
                    PROCEDURE_ALIASES[
                        provider_counter
                        % len(
                            PROCEDURE_ALIASES
                        )
                    ]
                )


                # =========================================
                # 서로 다른 가격
                # =========================================

                price_min = (
                    PRICE_BASES[
                        provider_counter
                        % len(
                            PRICE_BASES
                        )
                    ]
                )

                price_max = (
                    price_min
                    + 300_000
                )


                source_style = (
                    config[
                        "source_style"
                    ]
                )


                # =========================================
                # CONFLICTING 병원은
                # 동일 provider에 서로 다른 두 source 생성
                # =========================================

                if (
                    source_style
                    == "CONFLICTING"
                ):

                    # -------------------------------------
                    # 오래된 홈페이지 가격
                    # -------------------------------------

                    website_payload = (
                        f"{provider.name} "
                        f"{procedure_text} "
                        f"{price_min // 10_000}만원부터"
                    )


                    add_raw_evidence(
                        db=db,
                        hospital_id=hospital.id,
                        provider_id=provider.id,
                        source_type="WEBSITE",
                        source_reference=(
                            "/vision/event"
                        ),
                        raw_payload=(
                            website_payload
                        ),
                        observed_at=(
                            datetime(
                                2026,
                                5,
                                1,
                                9,
                                0,
                                0,
                            )
                        ),
                    )


                    # -------------------------------------
                    # 더 최근의 병원 관리자 입력
                    #
                    # 홈페이지보다 20만원 높게 입력
                    # → source conflict
                    # -------------------------------------

                    admin_price_min = (
                        price_min
                        + 200_000
                    )

                    admin_price_max = (
                        price_max
                        + 200_000
                    )


                    admin_payload = (
                        f"PROVIDER={provider.name}\n"
                        f"ITEM={procedure_text}\n"
                        f"PRICE_MIN={admin_price_min}\n"
                        f"PRICE_MAX={admin_price_max}\n"
                        f"UPDATED_BY=HOSPITAL_ADMIN"
                    )


                    add_raw_evidence(
                        db=db,
                        hospital_id=hospital.id,
                        provider_id=provider.id,
                        source_type="ADMIN",
                        source_reference=(
                            "hospital_admin"
                        ),
                        raw_payload=(
                            admin_payload
                        ),
                        observed_at=(
                            datetime(
                                2026,
                                8,
                                20,
                                10,
                                0,
                                0,
                            )
                        ),
                    )


                else:

                    raw_payload = (
                        build_raw_payload(
                            source_style=source_style,
                            hospital_name=hospital.name,
                            provider_name=provider.name,
                            procedure_text=procedure_text,
                            price_min=price_min,
                            price_max=price_max,
                        )
                    )


                    add_raw_evidence(
                        db=db,
                        hospital_id=hospital.id,
                        provider_id=provider.id,
                        source_type=source_style,
                        source_reference=(
                            f"synthetic/"
                            f"hospital_"
                            f"{hospital_index}"
                        ),
                        raw_payload=(
                            raw_payload
                        ),
                        observed_at=(
                            datetime(
                                2026,
                                8,
                                20,
                                9,
                                0,
                                0,
                            )
                            -
                            timedelta(
                                days=(
                                    hospital_index
                                    % 4
                                )
                            )
                        ),
                    )


                # =========================================
                # Appointment slots
                #
                # Offer ingestion 문제와
                # 예약 transaction 문제를 지금은 분리.
                #
                # Availability normalization은
                # 이후 별도 layer로 확장 가능.
                # =========================================

                slot_times = [

                    BASE_DATE
                    + timedelta(
                        hours=1
                        + (
                            provider_counter
                            % 3
                        )
                    ),

                    BASE_DATE
                    + timedelta(
                        hours=5,
                        minutes=20,
                    ),

                    BASE_DATE
                    + timedelta(
                        hours=6,
                    ),

                    BASE_DATE
                    + timedelta(
                        hours=7,
                        minutes=30,
                    ),

                    BASE_DATE
                    + timedelta(
                        days=1,
                        hours=6,
                    ),
                ]


                for slot_time in slot_times:

                    slot = AppointmentSlot(
                        provider_id=provider.id,
                        start_time=slot_time,
                        status="AVAILABLE",
                    )

                    db.add(
                        slot
                    )


        # =================================================
        # Hospital #8:
        #
        # 특정 의사를 명시하지 않은
        # 병원 전체 generic offer도 하나 추가
        #
        # 이건 normalizer가 자동 확정하면 안 되고
        # REVIEW_REQUIRED 후보가 될 수 있음.
        # =================================================

        hospital_8 = (
            db.query(Hospital)
            .order_by(
                Hospital.id
            )
            .offset(7)
            .first()
        )


        generic_payload = (
            "스마일라식 169만원부터. "
            "의료진 지정 시 추가비용이 발생할 수 있습니다."
        )


        add_raw_evidence(
            db=db,
            hospital_id=hospital_8.id,
            provider_id=None,
            source_type="FREE_TEXT",
            source_reference=(
                "hospital_generic_event"
            ),
            raw_payload=(
                generic_payload
            ),
            observed_at=datetime(
                2026,
                8,
                19,
                12,
                0,
                0,
            ),
        )


        db.commit()


        # =================================================
        # 결과 확인
        # =================================================

        hospital_count = (
            db.query(Hospital)
            .count()
        )

        provider_count = (
            db.query(Provider)
            .count()
        )

        raw_count = (
            db.query(
                RawOfferEvidence
            )
            .count()
        )

        canonical_count = (
            db.query(
                ProviderOffer
            )
            .count()
        )

        slot_count = (
            db.query(
                AppointmentSlot
            )
            .count()
        )


        print(
            "MARKET SEED: PASS"
        )

        print(
            "HOSPITALS:",
            hospital_count,
        )

        print(
            "PROVIDERS:",
            provider_count,
        )

        print(
            "RAW OFFER EVIDENCE:",
            raw_count,
        )

        print(
            "CANONICAL OFFERS:",
            canonical_count,
        )

        print(
            "APPOINTMENT SLOTS:",
            slot_count,
        )


    finally:

        db.close()


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    seed_market()