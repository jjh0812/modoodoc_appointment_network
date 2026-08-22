import json
import os

from dotenv import load_dotenv

from openai import OpenAI


# =========================================================
# Environment
#
# backend/.env
#
# OPENAI_API_KEY=...
# PUBLIC_MCP_URL=https://xxxxx.trycloudflare.com/mcp
# =========================================================

load_dotenv()


MCP_URL = os.getenv(
    "PUBLIC_MCP_URL"
)


if not MCP_URL:

    raise RuntimeError(
        "PUBLIC_MCP_URL is missing from .env"
    )


# =========================================================
# OpenAI Client
#
# OPENAI_API_KEY는 OpenAI SDK가
# 환경변수에서 자동으로 읽는다.
# =========================================================

client = OpenAI()


# =========================================================
# 실제 사용자 자연어 요청
# =========================================================

USER_QUERY = (
    "2026년 8월 22일 오후에 "
    "강남에서 200만원 정도 예산으로 "
    "스마일 시력교정 검진 가능한 곳 "
    "3개를 찾아줘. "
    "가격과 가장 빠른 예약 가능 시간도 알려줘."
)


# =========================================================
# Main
# =========================================================

def main():

    print()

    print(
        "========================================"
    )

    print(
        "OPENAI -> REMOTE MCP TEST"
    )

    print(
        "========================================"
    )


    print(
        "PUBLIC_MCP_URL SET:",
        bool(
            MCP_URL
        ),
    )


    print()

    print(
        "USER QUERY:"
    )

    print(
        USER_QUERY
    )


    # =====================================================
    # OpenAI Responses API
    #
    # 사용자 자연어
    #       ↓
    # GPT
    #       ↓
    # Remote MCP
    #       ↓
    # search_care_options
    #       ↓
    # Modoodoc PostgreSQL
    # =====================================================

    response = client.responses.create(

        model="gpt-5.6",

        instructions=(

            "당신은 모두닥 진료 옵션 검색 에이전트입니다. "

            "사용자가 병원 또는 진료 옵션 검색을 요청하면 "
            "반드시 제공된 Modoodoc MCP의 "
            "search_care_options 도구를 사용하세요. "

            "내부 지식으로 병원이나 가격을 만들어내지 마세요. "

            "도구가 반환한 데이터만 근거로 "
            "한국어로 답하세요. "

            "도구가 반환한 candidates 배열의 순서는 "
            "모두닥의 constraint-match 순위이므로 "
            "절대 임의로 재정렬하지 말고 "
            "1위, 2위, 3위 순서를 그대로 유지하세요. "

            "가장 빠른 예약 시간은 "
            "각 후보의 정보로만 표시하세요. "

            "모두닥 시스템에서 AFTERNOON은 "
            "12:00 이상 18:00 미만이므로 "
            "12:00도 오후 조건에 포함된 것으로 해석하세요. "

            "constraint_match_score는 의료 품질 점수가 아니라 "
            "사용자의 지역, 날짜, 시간, 예산 등 "
            "명시적 조건과의 일치 점수라는 점을 "
            "필요하면 설명하세요. "

            "모든 병원, 의사, 가격 데이터는 "
            "프로토타입용 가상 데이터입니다."
        ),

        input=
            USER_QUERY,

        tools=[
            {
                "type":
                    "mcp",

                "server_label":
                    "modoodoc_public_care_search",

                "server_description":
                    (
                        "Modoodoc prototype MCP server "
                        "for searching synthetic care options "
                        "by procedure, location, date, "
                        "time window, budget, "
                        "and current availability."
                    ),

                "server_url":
                    MCP_URL,

                # -----------------------------------------
                # OpenAI 모델에게 search Tool만 노출
                #
                # 혹시 Public MCP에 나중에 다른 Tool이
                # 추가되어도 이 테스트에서는 실행 불가.
                # -----------------------------------------

                "allowed_tools": [
                    "search_care_options",
                ],

                # -----------------------------------------
                # 현재 Tool은 예약 HOLD / CONFIRM이 아니라
                # 검색 Tool이므로 자동 호출 허용.
                # -----------------------------------------

                "require_approval":
                    "never",
            },
        ],
    )


    # =====================================================
    # 실제 MCP trace 검증
    # =====================================================

    saw_mcp_list_tools = False

    saw_mcp_call = False

    successful_search_call = False

    candidate_count = 0


    print()

    print(
        "========================================"
    )

    print(
        "OPENAI RESPONSE TRACE"
    )

    print(
        "========================================"
    )


    for item in response.output:

        item_type = getattr(
            item,
            "type",
            None,
        )


        print()

        print(
            "OUTPUT TYPE:",
            item_type,
        )


        # =================================================
        # OpenAI가 MCP server의 Tool schema를 읽었는지
        # =================================================

        if item_type == "mcp_list_tools":

            saw_mcp_list_tools = True


            print(
                "MCP SERVER:",
                getattr(
                    item,
                    "server_label",
                    None,
                ),
            )


            tools = getattr(
                item,
                "tools",
                [],
            )


            tool_names = [

                getattr(
                    tool,
                    "name",
                    None,
                )

                for tool
                in tools
            ]


            print(
                "MCP TOOLS:",
                tool_names,
            )


        # =================================================
        # OpenAI가 실제 Tool을 호출했는지
        # =================================================

        elif item_type == "mcp_call":

            saw_mcp_call = True


            tool_name = getattr(
                item,
                "name",
                None,
            )


            arguments = getattr(
                item,
                "arguments",
                None,
            )


            error = getattr(
                item,
                "error",
                None,
            )


            mcp_output = getattr(
                item,
                "output",
                None,
            )


            print(
                "TOOL NAME:",
                tool_name,
            )


            print(
                "ARGUMENTS:",
                arguments,
            )


            print(
                "ERROR:",
                error,
            )


            print(
                "MCP OUTPUT:"
            )


            print(
                mcp_output
            )


            # =============================================
            # 실제 search 결과도 검증
            #
            # MCP를 불렀다는 사실만으로 PASS하지 않는다.
            #
            # candidates > 0이어야 한다.
            # =============================================

            if (
                tool_name
                == "search_care_options"

                and

                error is None

                and

                mcp_output
            ):

                try:

                    parsed_output = (
                        json.loads(
                            mcp_output
                        )
                    )


                    candidates = (
                        parsed_output.get(
                            "candidates",
                            [],
                        )
                    )


                    candidate_count = max(
                        candidate_count,
                        len(
                            candidates
                        ),
                    )


                    if candidates:

                        canonical_codes_ok = all(

                            candidate.get(
                                "procedure_code"
                            )
                            ==
                            "VISION_CORRECTION_SMILE"

                            for candidate
                            in candidates
                        )


                        if canonical_codes_ok:

                            successful_search_call = True


                except json.JSONDecodeError:

                    pass


    # =====================================================
    # GPT 최종 자연어 답변
    # =====================================================

    print()

    print(
        "========================================"
    )

    print(
        "GPT FINAL ANSWER"
    )

    print(
        "========================================"
    )


    print(
        response.output_text
    )


    # =====================================================
    # 최종 판정
    #
    # 이제 다음을 모두 만족해야 PASS:
    #
    # 1. MCP Tool 목록 확인
    # 2. MCP Tool 실제 호출
    # 3. candidates > 0
    # 4. canonical procedure code 정상
    # 5. GPT 최종 답변 존재
    # =====================================================

    passed = (

        saw_mcp_list_tools

        and

        saw_mcp_call

        and

        successful_search_call

        and

        candidate_count > 0

        and

        bool(
            response.output_text.strip()
        )
    )


    print()

    print(
        "========================================"
    )

    print(
        "FINAL RESULT"
    )

    print(
        "========================================"
    )


    print(
        "MCP TOOL LIST SEEN:",
        saw_mcp_list_tools,
    )


    print(
        "MCP TOOL CALLED:",
        saw_mcp_call,
    )


    print(
        "SUCCESSFUL SEARCH CALL:",
        successful_search_call,
    )


    print(
        "CANDIDATE COUNT:",
        candidate_count,
    )


    if passed:

        print()

        print(
            "OPENAI -> REMOTE MCP: PASS"
        )


    else:

        print()

        print(
            "OPENAI -> REMOTE MCP: FAIL"
        )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    main()