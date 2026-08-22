from datetime import date
from typing import Literal

from mcp.server.mcpserver import MCPServer

from app.database import SessionLocal

from app.models import (
    CandidateMatch,
)

from app.services.appointment_service import (
    AppointmentServiceError,
    confirm_slot_hold,
)

from app.services.care_option_match_service import (
    search_care_options as search_care_options_core,
)

from app.services.hold_service import (
    HoldServiceError,
    create_slot_hold,
)


# =========================================================
# MCP Server
# =========================================================

mcp = MCPServer(
    "Modoodoc Executable Decision Network"
)


# =========================================================
# Search 결과 JSON 변환
# =========================================================

def serialize_search_result(
    result: dict,
):

    serialized_candidates = []


    for candidate in result["candidates"]:

        serialized_candidate = {
            **candidate,

            "earliest_slot_time":
                candidate[
                    "earliest_slot_time"
                ].isoformat(),
        }


        serialized_candidates.append(
            serialized_candidate
        )


    return {
        "intent_id":
            result["intent_id"],

        "candidates":
            serialized_candidates,
    }


# =========================================================
# MCP TOOL 1
#
# search_care_options
# =========================================================

@mcp.tool()
def search_care_options(
    procedure_code: str,
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

    constraint_match_score is NOT a medical quality score.
    It only measures fit with the user's stated constraints.
    """

    # -----------------------------------------------------
    # 날짜 문자열 → Python date
    # -----------------------------------------------------

    parsed_date = (
        date.fromisoformat(
            preferred_date
        )
    )


    # -----------------------------------------------------
    # limit 방어
    # -----------------------------------------------------

    if limit < 1:
        limit = 1

    if limit > 10:
        limit = 10


    # -----------------------------------------------------
    # 기존 Modoodoc Core 사용
    # -----------------------------------------------------

    db = SessionLocal()


    try:

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
                    "CHATGPT_MCP",

                raw_query=
                    raw_query,

                limit=
                    limit,
            )
        )


        return (
            serialize_search_result(
                result
            )
        )


    finally:

        db.close()


# =========================================================
# MCP TOOL 2
#
# hold_care_option
#
# CandidateMatch만 받는다.
#
# AI가 slot_id를 임의로 조립하지 않는다.
# =========================================================

@mcp.tool()
def hold_care_option(
    candidate_match_id: int,
) -> dict:

    """
    Hold the executable slot associated with a previously
    returned care-option candidate.

    This should be called only after the user selects that
    candidate.

    A successful hold lasts five minutes.
    """

    db = SessionLocal()


    try:

        # =================================================
        # Candidate 조회
        # =================================================

        candidate = (
            db.query(
                CandidateMatch
            )
            .filter(
                CandidateMatch.id
                == candidate_match_id
            )
            .first()
        )


        if candidate is None:

            return {
                "ok": False,
                "status_code": 404,
                "error":
                    "Candidate match not found",
            }


        # =================================================
        # 실행 가능한 slot 확인
        # =================================================

        if (
            candidate.earliest_slot_id
            is None
        ):

            return {
                "ok": False,
                "status_code": 409,
                "error":
                    "Candidate has no executable slot",
            }


        # =================================================
        # 공통 HOLD Core
        # =================================================

        hold = (
            create_slot_hold(

                db=db,

                slot_id=
                    candidate
                    .earliest_slot_id,

                source=
                    "CHATGPT_MCP",

                candidate_match_id=
                    candidate.id,
            )
        )


        # =================================================
        # 결과
        # =================================================

        return {

            "ok":
                True,

            "candidate_match_id":
                candidate.id,

            "intent_id":
                candidate.intent_id,

            "provider_id":
                candidate.provider_id,

            "hold_id":
                hold.id,

            "slot_id":
                hold.slot_id,

            "status":
                hold.status,

            "expires_at":
                hold.expires_at
                .isoformat(),
        }


    except HoldServiceError as error:

        return {

            "ok":
                False,

            "status_code":
                error.status_code,

            "error":
                error.detail,
        }


    finally:

        db.close()


# =========================================================
# MCP TOOL 3
#
# confirm_appointment
#
# HOLD → 실제 Appointment 확정
#
# 중요한 write action이므로
# user_confirmed=True가 반드시 필요하다.
# =========================================================

@mcp.tool()
def confirm_appointment(
    hold_id: int,
    user_confirmed: bool = False,
) -> dict:

    """
    Confirm a previously created appointment hold.

    This is a write action that creates a real appointment
    record in the prototype database.

    Call this only after the user explicitly confirms the
    booking. Pass user_confirmed=true only after that
    confirmation.
    """

    # =====================================================
    # 1. 사용자 명시적 확인 없이는 실행 금지
    # =====================================================

    if not user_confirmed:

        return {

            "ok":
                False,

            "status_code":
                400,

            "error":
                "Explicit user confirmation is required",
        }


    # =====================================================
    # 2. 같은 Hold에는 항상 같은 idempotency key
    #
    # 예:
    #
    # Hold #7
    #
    # ↓
    #
    # mcp-confirm-hold-7
    #
    # AI가 같은 confirm을 100번 retry해도
    # 같은 transaction으로 처리된다.
    # =====================================================

    idempotency_key = (
        f"mcp-confirm-hold-{hold_id}"
    )


    db = SessionLocal()


    try:

        appointment = (
            confirm_slot_hold(

                db=db,

                hold_id=
                    hold_id,

                idempotency_key=
                    idempotency_key,
            )
        )


        return {

            "ok":
                True,

            "appointment_id":
                appointment.id,

            "hold_id":
                appointment.hold_id,

            "slot_id":
                appointment.slot_id,

            "source":
                appointment.source,

            "status":
                appointment.status,

            "idempotency_key":
                appointment.idempotency_key,

            "created_at":
                appointment.created_at
                .isoformat(),
        }


    except AppointmentServiceError as error:

        return {

            "ok":
                False,

            "status_code":
                error.status_code,

            "error":
                error.detail,
        }


    finally:

        db.close()


# =========================================================
# MCP Server 실행
#
# Next.js    : 3000
# FastAPI    : 8001
# MCP        : 8002
# PostgreSQL : 5434
# =========================================================

if __name__ == "__main__":

    mcp.run(
        transport="streamable-http",

        host="127.0.0.1",

        port=8002,

        streamable_http_path="/mcp",

        stateless_http=True,

        json_response=True,
    )