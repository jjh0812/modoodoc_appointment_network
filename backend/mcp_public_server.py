import os

from datetime import date
from typing import Literal
from urllib.parse import urlparse

from dotenv import load_dotenv

from mcp.server.mcpserver import MCPServer

from mcp.server.transport_security import (
    TransportSecuritySettings,
)

from app.database import SessionLocal

from app.services.care_option_match_service import (
    search_care_options as search_care_options_core,
)


# =========================================================
# Environment
#
# Cloudflare Quick Tunnel URL은 실행할 때마다
# 바뀔 수 있다.
#
# 따라서 Python 코드에 URL을 박아두지 않고
# backend/.env에서 읽는다.
#
# 예:
#
# PUBLIC_MCP_URL=
# https://xxxxx.trycloudflare.com/mcp
# =========================================================

load_dotenv()


PUBLIC_MCP_URL = os.getenv(
    "PUBLIC_MCP_URL"
)


if not PUBLIC_MCP_URL:

    raise RuntimeError(
        "PUBLIC_MCP_URL is missing from .env"
    )


# =========================================================
# URL 분해
#
# 예:
#
# PUBLIC_MCP_URL
# =
# https://abc.trycloudflare.com/mcp
#
#
# PUBLIC_MCP_HOST
# =
# abc.trycloudflare.com
#
#
# PUBLIC_MCP_ORIGIN
# =
# https://abc.trycloudflare.com
# =========================================================

parsed_public_url = urlparse(
    PUBLIC_MCP_URL
)


if (
    parsed_public_url.scheme
    not in {
        "http",
        "https",
    }
    or
    not parsed_public_url.netloc
):

    raise RuntimeError(
        "PUBLIC_MCP_URL is invalid"
    )


PUBLIC_MCP_HOST = (
    parsed_public_url.netloc
)


PUBLIC_MCP_ORIGIN = (
    f"{parsed_public_url.scheme}://"
    f"{parsed_public_url.netloc}"
)


# =========================================================
# PUBLIC SEARCH-ONLY MCP
#
# 외부 AI 데모용.
#
# 외부에는 검색 기능만 공개한다.
#
# 여기에는 절대:
#
# hold_care_option
# confirm_appointment
#
# 를 등록하지 않는다.
#
#
# 주의:
#
# search_care_options 자체는
#
# PatientIntent
# CandidateMatch
# SHOWN DecisionEvent
#
# 등을 기록할 수 있다.
#
# 따라서 DB 전체 기준의 완전한 read-only가 아니라
# "예약 transaction write가 없는 search-only MCP"다.
# =========================================================

mcp = MCPServer(
    "Modoodoc Public Care Search"
)


# =========================================================
# 검색 결과 serialization
# =========================================================

def serialize_search_result(
    result: dict,
):

    candidates = []


    for candidate in result["candidates"]:

        serialized = {
            **candidate,

            "earliest_slot_time":
                candidate[
                    "earliest_slot_time"
                ].isoformat(),
        }


        candidates.append(
            serialized
        )


    return {
        "intent_id":
            result["intent_id"],

        "candidates":
            candidates,
    }


# =========================================================
# PUBLIC TOOL
#
# search_care_options
#
# 현재 외부 MCP에 공개되는 유일한 Tool.
#
#
# procedure_code를 Literal로 제한한 이유:
#
# GPT가
#
# SMILE
# SMILE_LASIK
# SMILE_LASIK_EXAM
#
# 같은 임의의 내부 코드를 추측하지 못하게 하고
#
# 실제 canonical code:
#
# VISION_CORRECTION_SMILE
#
# 를 MCP schema 자체가 알려주기 위함.
# =========================================================

@mcp.tool()
def search_care_options(
    procedure_code: Literal[
        "VISION_CORRECTION_SMILE",
    ],
    preferred_date: str,
    district: str | None = None,
    time_window: Literal[
        "MORNING",
        "AFTERNOON",
        "EVENING",
        "ANY",
    ] = "ANY",
    budget_max: int | None = None,
    raw_query: str | None = None,
    limit: int = 3,
) -> dict:

    """
    Search executable healthcare options matching the user's
    explicit procedure, location, date, time, and budget.

    This public MCP exposes search only.
    It does not expose booking HOLD or CONFIRM actions.

    constraint_match_score is NOT a medical quality score.
    It measures fit with the user's stated constraints.
    """

    # =====================================================
    # 1. 날짜 문자열 → Python date
    # =====================================================

    parsed_date = (
        date.fromisoformat(
            preferred_date
        )
    )


    # =====================================================
    # 2. limit 방어
    #
    # 외부 AI가 이상한 숫자를 보내더라도
    # 1~10 사이로 제한.
    # =====================================================

    if limit < 1:

        limit = 1


    if limit > 10:

        limit = 10


    # =====================================================
    # 3. PostgreSQL Session
    # =====================================================

    db = SessionLocal()


    try:

        # =================================================
        # 4. 기존 Modoodoc Core 사용
        #
        # Public MCP 전용 검색 로직을 따로 만들지 않는다.
        #
        # FastAPI / MCP가 같은:
        #
        # intent normalization
        # canonical offers
        # availability
        # constraint matching
        #
        # 로직을 공유한다.
        # =================================================

        result = (
            search_care_options_core(

                db=db,

                procedure_code=
                    procedure_code,

                district=
                    district,

                preferred_date=
                    parsed_date,

                time_window=
                    time_window,

                budget_max=
                    budget_max,

                source=
                    "PUBLIC_MCP",

                raw_query=
                    raw_query,

                limit=
                    limit,
            )
        )


        # =================================================
        # 5. MCP가 반환할 수 있는 JSON 형태로 변환
        # =================================================

        return (
            serialize_search_result(
                result
            )
        )


    finally:

        db.close()


# =========================================================
# Server
#
# Local full MCP
#     127.0.0.1:8002
#
# Public search-only MCP
#     127.0.0.1:8003
#
#
# Cloudflare:
#
# PUBLIC_MCP_URL
#        ↓
# Cloudflare Tunnel
#        ↓
# 127.0.0.1:8003/mcp
# =========================================================

if __name__ == "__main__":

    # =====================================================
    # DNS Rebinding Protection
    #
    # 보안 검사를 끄지 않는다.
    #
    # 대신 현재 .env에 등록된
    # Cloudflare hostname만 명시적으로 허용한다.
    #
    # 예:
    #
    # abc.trycloudflare.com
    # =====================================================

    security = TransportSecuritySettings(

        enable_dns_rebinding_protection=True,

        allowed_hosts=[

            PUBLIC_MCP_HOST,

            "127.0.0.1:8003",

            "localhost:8003",
        ],

        allowed_origins=[

            PUBLIC_MCP_ORIGIN,

            "http://127.0.0.1:8003",

            "http://localhost:8003",
        ],
    )


    # =====================================================
    # MCP Server 실행
    # =====================================================

    mcp.run(

        transport=
            "streamable-http",

        host=
            "127.0.0.1",

        port=
            8003,

        streamable_http_path=
            "/mcp",

        stateless_http=
            True,

        json_response=
            True,

        transport_security=
            security,
    )