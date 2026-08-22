import asyncio
import json
import os

from dotenv import load_dotenv

from mcp import ClientSession

from mcp.client.streamable_http import (
    streamable_http_client,
)


# =========================================================
# Environment
#
# Cloudflare Quick Tunnel 주소를
# 코드에 직접 박아두지 않는다.
#
# backend/.env:
#
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
# MCP text JSON → Python dict
# =========================================================

def parse_tool_result(
    result,
):

    for content in result.content:

        text = getattr(
            content,
            "text",
            None,
        )


        if text:

            return json.loads(
                text
            )


    raise RuntimeError(
        "No JSON text found in MCP result"
    )


# =========================================================
# Main
# =========================================================

async def main():

    print()

    print(
        "========================================"
    )

    print(
        "PUBLIC MCP ENDPOINT"
    )

    print(
        "========================================"
    )


    # 실제 URL 전체를 로그에 출력하지 않고
    # 설정이 존재한다는 것만 확인
    print(
        "PUBLIC_MCP_URL SET:",
        bool(
            MCP_URL
        ),
    )


    # =====================================================
    # 1. 인터넷 HTTPS MCP endpoint 연결
    # =====================================================

    async with streamable_http_client(
        MCP_URL
    ) as (
        read_stream,
        write_stream,
    ):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            # =============================================
            # 2. MCP Handshake
            # =============================================

            initialization = (
                await session.initialize()
            )


            print()

            print(
                "========================================"
            )

            print(
                "PUBLIC MCP CONNECTION"
            )

            print(
                "========================================"
            )


            print(
                "SERVER:",
                initialization.server_info.name,
            )


            # =============================================
            # 3. 외부에 노출된 Tool 확인
            # =============================================

            tools = (
                await session.list_tools()
            )


            tool_names = [

                tool.name

                for tool
                in tools.tools
            ]


            print(
                "TOOLS:",
                tool_names,
            )


            # =============================================
            # 4. Public Search 호출
            # =============================================

            result = (
                await session.call_tool(

                    "search_care_options",

                    arguments={

                        "procedure_code":
                            "VISION_CORRECTION_SMILE",

                        "district":
                            "강남",

                        "preferred_date":
                            "2026-08-22",

                        "time_window":
                            "AFTERNOON",

                        "budget_max":
                            2000000,

                        "raw_query":
                            (
                                "8월 22일 오후 강남에서 "
                                "200만원 정도로 "
                                "스마일 시력교정 검진 "
                                "가능한 곳 찾아줘"
                            ),

                        "limit":
                            3,
                    },
                )
            )


            data = (
                parse_tool_result(
                    result
                )
            )


            # =============================================
            # 5. 결과 출력
            # =============================================

            print()

            print(
                "========================================"
            )

            print(
                "PUBLIC MCP SEARCH RESULT"
            )

            print(
                "========================================"
            )


            print(
                "INTENT ID:",
                data[
                    "intent_id"
                ],
            )


            candidates = (
                data[
                    "candidates"
                ]
            )


            print(
                "CANDIDATE COUNT:",
                len(candidates),
            )


            for index, candidate in enumerate(
                candidates,
                start=1,
            ):

                print()

                print(
                    f"CANDIDATE {index}"
                )


                print(
                    "HOSPITAL:",
                    candidate[
                        "hospital_name"
                    ],
                )


                print(
                    "PROVIDER:",
                    candidate[
                        "provider_name"
                    ],
                )


                print(
                    "SLOT:",
                    candidate[
                        "earliest_slot_time"
                    ],
                )


                print(
                    "SCORE:",
                    candidate[
                        "constraint_match_score"
                    ],
                )


            # =============================================
            # 6. 외부 노출 안전성 검사
            #
            # 외부 MCP에는 search만 있어야 한다.
            # =============================================

            passed = (

                tool_names
                ==
                [
                    "search_care_options"
                ]

                and

                len(
                    candidates
                )
                > 0
            )


            print()


            if passed:

                print(
                    "PUBLIC HTTPS MCP: PASS"
                )


            else:

                print(
                    "PUBLIC HTTPS MCP: FAIL"
                )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )