import asyncio
import json

from mcp import ClientSession

from mcp.client.streamable_http import (
    streamable_http_client,
)


MCP_URL = (
    "http://127.0.0.1:8002/mcp"
)


# =========================================================
# MCP text JSON → dict
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
            # 1. Initialize
            # =============================================

            initialization = (
                await session.initialize()
            )


            print()

            print(
                "========================================"
            )

            print(
                "MCP CONNECTION"
            )

            print(
                "========================================"
            )


            print(
                "SERVER:",
                initialization.server_info.name,
            )


            # =============================================
            # 2. Tools
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
            # 3. SEARCH
            # =============================================

            search_result = (
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


            search_data = (
                parse_tool_result(
                    search_result
                )
            )


            candidates = (
                search_data[
                    "candidates"
                ]
            )


            print()

            print(
                "========================================"
            )

            print(
                "MCP SEARCH"
            )

            print(
                "========================================"
            )


            print(
                "INTENT:",
                search_data[
                    "intent_id"
                ],
            )


            print(
                "CANDIDATES:",
                len(candidates),
            )


            if not candidates:

                raise RuntimeError(
                    "No candidates returned"
                )


            # =============================================
            # 4. 1위 후보
            # =============================================

            winner = (
                candidates[0]
            )


            print(
                "WINNER:",
                winner[
                    "candidate_match_id"
                ],
                winner[
                    "hospital_name"
                ],
                winner[
                    "provider_name"
                ],
                winner[
                    "earliest_slot_time"
                ],
            )


            # =============================================
            # 5. HOLD
            # =============================================

            hold_result = (
                await session.call_tool(

                    "hold_care_option",

                    arguments={
                        "candidate_match_id":
                            winner[
                                "candidate_match_id"
                            ],
                    },
                )
            )


            hold_data = (
                parse_tool_result(
                    hold_result
                )
            )


            print()

            print(
                "========================================"
            )

            print(
                "MCP HOLD"
            )

            print(
                "========================================"
            )


            print(
                json.dumps(
                    hold_data,
                    ensure_ascii=False,
                    indent=2,
                )
            )


            if not hold_data.get(
                "ok"
            ):

                raise RuntimeError(
                    "MCP HOLD failed"
                )


            hold_id = (
                hold_data[
                    "hold_id"
                ]
            )


            # =============================================
            # 6. CONFIRM
            #
            # 테스트에서는 명시적으로
            # user_confirmed=True를 전달
            # =============================================

            confirm_result = (
                await session.call_tool(

                    "confirm_appointment",

                    arguments={

                        "hold_id":
                            hold_id,

                        "user_confirmed":
                            True,
                    },
                )
            )


            confirm_data = (
                parse_tool_result(
                    confirm_result
                )
            )


            print()

            print(
                "========================================"
            )

            print(
                "MCP CONFIRM"
            )

            print(
                "========================================"
            )


            print(
                json.dumps(
                    confirm_data,
                    ensure_ascii=False,
                    indent=2,
                )
            )


            if not confirm_data.get(
                "ok"
            ):

                raise RuntimeError(
                    "MCP CONFIRM failed"
                )


            # =============================================
            # 7. 같은 CONFIRM 다시 retry
            #
            # 동일 Hold ID
            # → 동일 deterministic key
            # → 동일 Appointment
            # =============================================

            retry_result = (
                await session.call_tool(

                    "confirm_appointment",

                    arguments={

                        "hold_id":
                            hold_id,

                        "user_confirmed":
                            True,
                    },
                )
            )


            retry_data = (
                parse_tool_result(
                    retry_result
                )
            )


            print()

            print(
                "========================================"
            )

            print(
                "MCP CONFIRM RETRY"
            )

            print(
                "========================================"
            )


            print(
                json.dumps(
                    retry_data,
                    ensure_ascii=False,
                    indent=2,
                )
            )


            # =============================================
            # 8. Final PASS
            # =============================================

            passed = (

                "search_care_options"
                in tool_names

                and

                "hold_care_option"
                in tool_names

                and

                "confirm_appointment"
                in tool_names

                and

                hold_data.get("ok")
                is True

                and

                confirm_data.get("ok")
                is True

                and

                retry_data.get("ok")
                is True

                and

                confirm_data.get(
                    "appointment_id"
                )
                ==
                retry_data.get(
                    "appointment_id"
                )

                and

                confirm_data.get(
                    "status"
                )
                == "CONFIRMED"
            )


            print()


            if passed:

                print(
                    "MCP END-TO-END TRANSACTION: PASS"
                )

            else:

                print(
                    "MCP END-TO-END TRANSACTION: FAIL"
                )


if __name__ == "__main__":

    asyncio.run(
        main()
    )