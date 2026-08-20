import csv
import io
import json
import re

from dataclasses import dataclass, field
from datetime import datetime

from app.models import RawOfferEvidence


# =========================================================
# 모두닥 내부 표준 시술명
# =========================================================

CANONICAL_SMILE_CODE = (
    "VISION_CORRECTION_SMILE"
)

CANONICAL_SMILE_NAME = (
    "스마일 시력교정"
)


# =========================================================
# 병원마다 제각각 부르는 동일 시술명
#
# 현재 prototype에서는 모두 같은 canonical concept로
# 매핑한다.
# =========================================================

SMILE_ALIASES = [
    "SMILE LASIK",
    "시력교정 스마일",
    "스마일 시력교정",
    "스마일라식",
    "스마일 프로",
    "SMILE",
]


# =========================================================
# Extraction 결과
#
# 중요:
#
# 아직 ProviderOffer가 아니다.
#
# RAW에서 우리가 "읽어낸 후보"일 뿐이다.
# =========================================================

@dataclass
class ExtractedOfferCandidate:

    evidence_id: int

    hospital_id: int

    provider_id: int | None

    source_type: str

    observed_at: datetime | None


    # -----------------------------------------------------
    # 원문에서 읽어낸 시술명
    # -----------------------------------------------------

    procedure_text: str | None


    # -----------------------------------------------------
    # 모두닥 terminology mapping 결과
    # -----------------------------------------------------

    procedure_code: str | None

    procedure_name: str | None


    # -----------------------------------------------------
    # 가격
    # -----------------------------------------------------

    price_min: int | None

    price_max: int | None

    currency: str = "KRW"


    # -----------------------------------------------------
    # 기타 offer 정보
    # -----------------------------------------------------

    inspection_fee_included: bool | None = None

    conditional_discount: bool = False

    bookable: bool = True


    # -----------------------------------------------------
    # Extraction 신뢰도
    #
    # 이것은 "병원이 좋은가" 점수가 아니다.
    #
    # 우리가 RAW를 얼마나 확실하게
    # 구조화했는가에 대한 confidence다.
    # -----------------------------------------------------

    confidence: float = 1.0


    # -----------------------------------------------------
    # 자동 canonicalization을 막아야 하는 문제
    # -----------------------------------------------------

    review_reasons: list[str] = field(
        default_factory=list
    )


    # -----------------------------------------------------
    # 막을 정도는 아니지만
    # 이후 검색/표시에서 알아야 할 정보
    # -----------------------------------------------------

    warnings: list[str] = field(
        default_factory=list
    )


    @property
    def review_required(self):

        return (
            len(
                self.review_reasons
            )
            > 0
        )


# =========================================================
# 공통 helper
# =========================================================

def map_procedure(
    procedure_text: str | None,
):

    if not procedure_text:

        return (
            None,
            None,
        )


    normalized = (
        procedure_text
        .upper()
        .replace(" ", "")
    )


    for alias in SMILE_ALIASES:

        normalized_alias = (
            alias
            .upper()
            .replace(" ", "")
        )


        if (
            normalized_alias
            in normalized
        ):

            return (
                CANONICAL_SMILE_CODE,
                CANONICAL_SMILE_NAME,
            )


    return (
        None,
        None,
    )


# =========================================================
# 긴 텍스트 안에서 시술 alias 찾기
# =========================================================

def find_procedure_alias(
    text: str,
):

    # 긴 alias부터 찾는다.
    #
    # 예:
    # "SMILE LASIK"을
    # 단순 "SMILE"보다 먼저 매칭

    aliases = sorted(
        SMILE_ALIASES,
        key=len,
        reverse=True,
    )


    upper_text = (
        text.upper()
    )


    for alias in aliases:

        if (
            alias.upper()
            in upper_text
        ):

            return alias


    return None


# =========================================================
# "199만원" → 1,990,000
# =========================================================

def manwon_to_won(
    value: str,
):

    return (
        int(value)
        * 10_000
    )


# =========================================================
# ADMIN 형식
#
# KEY=VALUE
# KEY=VALUE
# =========================================================

def parse_key_value_payload(
    payload: str,
):

    result = {}


    for line in payload.splitlines():

        if "=" not in line:
            continue


        key, value = (
            line.split(
                "=",
                1,
            )
        )


        result[
            key.strip()
        ] = (
            value.strip()
        )


    return result


# =========================================================
# JSON_API
# =========================================================

def extract_json_api(
    evidence: RawOfferEvidence,
):

    data = json.loads(
        evidence.raw_payload
    )


    price = (
        data.get("price")
        or {}
    )


    return {
        "procedure_text":
            data.get("service"),

        "price_min":
            price.get("min"),

        "price_max":
            price.get("max"),

        "inspection_fee_included":
            data.get(
                "exam_fee_included"
            ),

        "conditional_discount":
            False,

        "bookable":
            data.get(
                "bookable",
                True,
            ),

        "confidence":
            0.99,
    }


# =========================================================
# CSV
# =========================================================

def extract_csv(
    evidence: RawOfferEvidence,
):

    reader = csv.DictReader(
        io.StringIO(
            evidence.raw_payload
        )
    )


    row = next(
        reader
    )


    return {
        "procedure_text":
            row.get("treatment"),

        "price_min":
            int(
                row["min_price"]
            ),

        "price_max":
            int(
                row["max_price"]
            ),

        "inspection_fee_included":
            (
                "검사비 포함"
                in row.get(
                    "memo",
                    "",
                )
            ),

        "conditional_discount":
            False,

        "bookable":
            True,

        "confidence":
            0.97,
    }


# =========================================================
# FREE_TEXT
#
# 예:
#
# 가상의사 07 원장
# 스마일 프로 199만원부터.
# 검사비 별도.
# 당일 수술 결정 시 추가 할인 가능.
# =========================================================

def extract_free_text(
    evidence: RawOfferEvidence,
):

    text = (
        evidence.raw_payload
    )


    procedure_text = (
        find_procedure_alias(
            text
        )
    )


    price_match = re.search(
        r"(\d{2,3})\s*만원",
        text,
    )


    price_min = None


    if price_match:

        price_min = (
            manwon_to_won(
                price_match.group(1)
            )
        )


    return {
        "procedure_text":
            procedure_text,

        "price_min":
            price_min,

        "price_max":
            None,

        "inspection_fee_included":
            (
                False
                if "검사비 별도" in text
                else None
            ),

        "conditional_discount":
            (
                "할인"
                in text
            ),

        "bookable":
            True,

        "confidence":
            0.82,
    }


# =========================================================
# ADMIN
# =========================================================

def extract_admin(
    evidence: RawOfferEvidence,
):

    data = (
        parse_key_value_payload(
            evidence.raw_payload
        )
    )


    price_min = (
        int(
            data["PRICE_MIN"]
        )
        if data.get(
            "PRICE_MIN"
        )
        else None
    )


    price_max = (
        int(
            data["PRICE_MAX"]
        )
        if data.get(
            "PRICE_MAX"
        )
        else None
    )


    inspection_value = (
        data.get(
            "INSPECTION_INCLUDED"
        )
    )


    inspection_fee_included = None


    if inspection_value == "Y":

        inspection_fee_included = True

    elif inspection_value == "N":

        inspection_fee_included = False


    bookable_value = (
        data.get(
            "BOOKABLE"
        )
    )


    bookable = (
        False
        if bookable_value == "N"
        else True
    )


    return {
        "procedure_text":
            data.get("ITEM"),

        "price_min":
            price_min,

        "price_max":
            price_max,

        "inspection_fee_included":
            inspection_fee_included,

        "conditional_discount":
            False,

        "bookable":
            bookable,

        "confidence":
            0.99,
    }


# =========================================================
# WEBSITE
#
# HTML처럼 생긴 데이터와
# 단순 홈페이지 텍스트를 둘 다 처리
# =========================================================

def extract_website(
    evidence: RawOfferEvidence,
):

    text = (
        evidence.raw_payload
    )


    procedure_text = None


    h3_match = re.search(
        r"<h3>(.*?)</h3>",
        text,
        flags=re.IGNORECASE,
    )


    if h3_match:

        procedure_text = (
            h3_match
            .group(1)
            .strip()
        )

    else:

        procedure_text = (
            find_procedure_alias(
                text
            )
        )


    # -----------------------------------------------------
    # 170~200만원
    # -----------------------------------------------------

    range_match = re.search(
        r"(\d{2,3})\s*~\s*(\d{2,3})\s*만원",
        text,
    )


    price_min = None
    price_max = None


    if range_match:

        price_min = (
            manwon_to_won(
                range_match.group(1)
            )
        )

        price_max = (
            manwon_to_won(
                range_match.group(2)
            )
        )


    else:

        # -------------------------------------------------
        # 170만원부터
        # -------------------------------------------------

        min_match = re.search(
            r"(\d{2,3})\s*만원",
            text,
        )


        if min_match:

            price_min = (
                manwon_to_won(
                    min_match.group(1)
                )
            )


    return {
        "procedure_text":
            procedure_text,

        "price_min":
            price_min,

        "price_max":
            price_max,

        "inspection_fee_included":
            None,

        "conditional_discount":
            False,

        "bookable":
            True,

        "confidence":
            0.86,
    }


# =========================================================
# NESTED_JSON
# =========================================================

def extract_nested_json(
    evidence: RawOfferEvidence,
):

    data = json.loads(
        evidence.raw_payload
    )


    products = (
        data.get(
            "products",
            []
        )
    )


    if not products:

        raise ValueError(
            "No products in nested JSON"
        )


    product = (
        products[0]
    )


    pricing = (
        product.get(
            "pricing",
            {},
        )
    )


    return {
        "procedure_text":
            product.get(
                "display"
            ),

        "price_min":
            pricing.get(
                "from"
            ),

        "price_max":
            pricing.get(
                "to"
            ),

        "inspection_fee_included":
            None,

        "conditional_discount":
            False,

        "bookable":
            True,

        "confidence":
            0.96,
    }


# =========================================================
# LEGACY_CSV
#
# DR,NM,LOW,HIGH,ETC
# =========================================================

def extract_legacy_csv(
    evidence: RawOfferEvidence,
):

    reader = csv.DictReader(
        io.StringIO(
            evidence.raw_payload
        )
    )


    row = next(
        reader
    )


    return {
        "procedure_text":
            row.get("NM"),

        "price_min":
            (
                int(
                    row["LOW"]
                )
                if row.get("LOW")
                else None
            ),

        "price_max":
            (
                int(
                    row["HIGH"]
                )
                if row.get("HIGH")
                else None
            ),

        "inspection_fee_included":
            None,

        "conditional_discount":
            False,

        "bookable":
            True,

        "confidence":
            0.90,
    }


# =========================================================
# SPARSE_TEXT
#
# 예:
# 스마일라식 169만원~
# 의료진 지정시 비용 상이
# =========================================================

def extract_sparse_text(
    evidence: RawOfferEvidence,
):

    text = (
        evidence.raw_payload
    )


    procedure_text = (
        find_procedure_alias(
            text
        )
    )


    price_match = re.search(
        r"(\d{2,3})\s*만원",
        text,
    )


    price_min = None


    if price_match:

        price_min = (
            manwon_to_won(
                price_match.group(1)
            )
        )


    return {
        "procedure_text":
            procedure_text,

        "price_min":
            price_min,

        "price_max":
            None,

        "inspection_fee_included":
            None,

        "conditional_discount":
            False,

        "bookable":
            True,

        "confidence":
            0.65,
    }


# =========================================================
# ADMIN_INCOMPLETE
#
# JSON이지만 일부 필드가 빠져 있음
# =========================================================

def extract_admin_incomplete(
    evidence: RawOfferEvidence,
):

    data = json.loads(
        evidence.raw_payload
    )


    return {
        "procedure_text":
            data.get(
                "procedure"
            ),

        "price_min":
            data.get(
                "starting_price"
            ),

        "price_max":
            None,

        "inspection_fee_included":
            None,

        "conditional_discount":
            False,

        "bookable":
            True,

        "confidence":
            0.78,
    }


# =========================================================
# Source type → parser
# =========================================================

EXTRACTORS = {

    "JSON_API":
        extract_json_api,

    "CSV":
        extract_csv,

    "FREE_TEXT":
        extract_free_text,

    "ADMIN":
        extract_admin,

    "WEBSITE":
        extract_website,

    "NESTED_JSON":
        extract_nested_json,

    "LEGACY_CSV":
        extract_legacy_csv,

    "SPARSE_TEXT":
        extract_sparse_text,

    "ADMIN_INCOMPLETE":
        extract_admin_incomplete,
}


# =========================================================
# RAW evidence 하나 → Extracted candidate
# =========================================================

def extract_offer_candidate(
    evidence: RawOfferEvidence,
):

    extractor = (
        EXTRACTORS.get(
            evidence.source_type
        )
    )


    if extractor is None:

        raise ValueError(
            "Unsupported source type: "
            f"{evidence.source_type}"
        )


    extracted = (
        extractor(
            evidence
        )
    )


    procedure_text = (
        extracted.get(
            "procedure_text"
        )
    )


    (
        procedure_code,
        procedure_name,
    ) = map_procedure(
        procedure_text
    )


    confidence = float(
        extracted.get(
            "confidence",
            1.0,
        )
    )


    review_reasons = []

    warnings = []


    # -----------------------------------------------------
    # Provider를 특정할 수 없는 병원 전체 offer
    #
    # 자동으로 의사에게 붙이면 안 된다.
    # -----------------------------------------------------

    if evidence.provider_id is None:

        review_reasons.append(
            "PROVIDER_UNRESOLVED"
        )

        confidence -= 0.20


    # -----------------------------------------------------
    # 시술명을 canonical terminology로
    # 매핑할 수 없는 경우
    # -----------------------------------------------------

    if procedure_code is None:

        review_reasons.append(
            "PROCEDURE_UNRESOLVED"
        )

        confidence -= 0.25


    # -----------------------------------------------------
    # 최소가격조차 없으면 자동 사용 불가
    # -----------------------------------------------------

    price_min = (
        extracted.get(
            "price_min"
        )
    )


    price_max = (
        extracted.get(
            "price_max"
        )
    )


    if price_min is None:

        review_reasons.append(
            "PRICE_MIN_MISSING"
        )

        confidence -= 0.25


    # -----------------------------------------------------
    # "~부터" 가격
    #
    # 사용할 수는 있지만
    # budget filtering에서 주의가 필요
    # -----------------------------------------------------

    if (
        price_min is not None
        and price_max is None
    ):

        warnings.append(
            "PRICE_RANGE_PARTIAL"
        )

        confidence -= 0.05


    confidence = max(
        0.0,
        min(
            confidence,
            1.0,
        ),
    )


    return ExtractedOfferCandidate(

        evidence_id=evidence.id,

        hospital_id=evidence.hospital_id,

        provider_id=evidence.provider_id,

        source_type=evidence.source_type,

        observed_at=evidence.observed_at,

        procedure_text=
            procedure_text,

        procedure_code=
            procedure_code,

        procedure_name=
            procedure_name,

        price_min=
            price_min,

        price_max=
            price_max,

        inspection_fee_included=
            extracted.get(
                "inspection_fee_included"
            ),

        conditional_discount=
            extracted.get(
                "conditional_discount",
                False,
            ),

        bookable=
            extracted.get(
                "bookable",
                True,
            ),

        confidence=
            confidence,

        review_reasons=
            review_reasons,

        warnings=
            warnings,
    )