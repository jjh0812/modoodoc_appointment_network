import json
import shutil
import subprocess
import sys
import time

from pathlib import Path

from urllib.error import URLError
from urllib.request import urlopen


# =========================================================
# Paths
# =========================================================

BACKEND_DIR = Path(
    __file__
).resolve().parent


PROJECT_DIR = (
    BACKEND_DIR.parent
)


FRONTEND_DIR = (
    PROJECT_DIR
    / "frontend"
)


BASE_URL = (
    "http://127.0.0.1:8001"
)


# =========================================================
# Test definitions
# =========================================================

SCRIPT_TESTS = [
    {
        "name":
            "Operational health and request tracing",

        "file":
            "operational_health_test.py",

        "expected":
            "OPERATIONAL HEALTH: PASS",
    },
    {
        "name":
            "Concurrent idempotency",

        "file":
            "idempotency_concurrency_test.py",

        "expected":
            "CONCURRENT IDEMPOTENCY: PASS",
    },
    {
        "name":
            "Expired HOLD protection",

        "file":
            "expired_hold_confirm_test.py",

        "expected":
            "EXPIRED HOLD CONFIRM: PASS",
    },
    {
        "name":
            "Idempotency key reuse protection",

        "file":
            "idempotency_key_reuse_test.py",

        "expected":
            "IDEMPOTENCY KEY REUSE: PASS",
    },
    {
        "name":
            "Decision Feedback E2E",

        "file":
            "decision_feedback_test.py",

        "expected":
            "DECISION FEEDBACK END-TO-END: PASS",
    },
]


# =========================================================
# Result storage
# =========================================================

results = []


def print_header(
    title: str,
):

    print()

    print(
        "=" * 60
    )

    print(
        title
    )

    print(
        "=" * 60
    )


def record(
    name: str,
    passed: bool,
    detail: str = "",
):

    results.append(
        {
            "name":
                name,

            "passed":
                passed,

            "detail":
                detail,
        }
    )


    status = (
        "PASS"
        if passed
        else "FAIL"
    )


    print(
        f"[{status}] {name}"
    )


    if detail:

        print(
            detail
        )


# =========================================================
# HTTP helpers
# =========================================================

def fetch_json(
    path: str,
    timeout: int = 5,
):

    with urlopen(
        BASE_URL + path,
        timeout=timeout,
    ) as response:

        return json.loads(
            response
            .read()
            .decode(
                "utf-8"
            )
        )


def api_is_ready():

    try:

        result = fetch_json(
            "/"
        )


        return (
            result.get(
                "status"
            )
            == "ok"
        )


    except Exception:

        return False


# =========================================================
# Temporary FastAPI server
# =========================================================

def ensure_fastapi():

    print_header(
        "1. FASTAPI AVAILABILITY"
    )


    # -----------------------------------------------------
    # 이미 8001에서 정상 FastAPI가 돌고 있으면 재사용
    # -----------------------------------------------------

    if api_is_ready():

        record(
            "FastAPI health",
            True,
            (
                "Existing FastAPI server found "
                "on 127.0.0.1:8001"
            ),
        )


        return None


    print(
        "FastAPI is not running."
    )

    print(
        "Starting temporary Uvicorn server..."
    )


    process = subprocess.Popen(

        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],

        cwd=
            str(
                BACKEND_DIR
            ),

        stdout=
            subprocess.DEVNULL,

        stderr=
            subprocess.DEVNULL,
    )


    # -----------------------------------------------------
    # 최대 20초 startup 대기
    # -----------------------------------------------------

    for _ in range(
        40
    ):

        if api_is_ready():

            record(
                "FastAPI health",
                True,
                "Temporary FastAPI server started.",
            )


            return process


        if (
            process.poll()
            is not None
        ):

            break


        time.sleep(
            0.5
        )


    record(
        "FastAPI health",
        False,
        (
            "Could not start FastAPI "
            "on port 8001."
        ),
    )


    if (
        process.poll()
        is None
    ):

        process.terminate()


    return False


# =========================================================
# Backend import check
# =========================================================

def backend_import_check():

    print_header(
        "2. BACKEND IMPORT CHECK"
    )


    code = r'''
from app.main import app

from app.services.appointment_service import (
    confirm_slot_hold,
)

from app.services.hold_service import (
    create_slot_hold,
)

from app.services.care_option_match_service import (
    search_care_options,
)

from app.services.decision_analytics_service import (
    get_decision_funnel,
)

from app.services.decision_feedback_service import (
    create_selection_feedback,
    create_no_selection_feedback,
)

from app.services.decision_feedback_analytics_service import (
    get_decision_feedback_summary,
)

print("BACKEND IMPORT CHECK: PASS")
'''


    run_python_check(
        name=
            "Backend core imports",

        code=
            code,

        expected=
            "BACKEND IMPORT CHECK: PASS",
    )


# =========================================================
# MCP registration check
# =========================================================

def mcp_registration_check():

    print_header(
        "3. MCP TOOL REGISTRATION"
    )


    code = r'''
import asyncio

from mcp_server import mcp


async def main():

    tools = await mcp.list_tools()

    names = [
        tool.name
        for tool
        in tools
    ]

    expected = [
        "search_care_options",
        "hold_care_option",
        "confirm_appointment",
    ]

    print("TOOLS:", names)

    if names != expected:
        raise RuntimeError(
            f"Unexpected MCP tools: {names}"
        )

    print("MCP TOOL REGISTRATION: PASS")


asyncio.run(main())
'''


    run_python_check(
        name=
            "MCP tools",

        code=
            code,

        expected=
            "MCP TOOL REGISTRATION: PASS",
    )


# =========================================================
# Demo Analytics exact validation
# =========================================================

def analytics_check(
    label: str,
):

    print_header(
        label
    )


    try:

        funnel = fetch_json(
            "/analytics/decision-funnel"
        )


        feedback = fetch_json(
            "/analytics/decision-feedback-summary"
        )


        hospitals = fetch_json(
            "/analytics/hospitals"
        )


        actual = (
            funnel[
                "funnel"
            ]
        )


        expected = {
            "searched":
                30,

            "shown":
                24,

            "selected":
                10,

            "held":
                10,

            "confirmed":
                5,
        }


        funnel_ok = (
            actual
            == expected
        )


        feedback_ok = (

            feedback[
                "selection_feedback"
            ][
                "feedback_count"
            ]
            == 10

            and

            feedback[
                "no_selection_feedback"
            ][
                "feedback_count"
            ]
            == 8
        )


        hospitals_ok = (
            hospitals[
                "hospital_count"
            ]
            == 3
        )


        passed = (

            funnel_ok

            and

            feedback_ok

            and

            hospitals_ok
        )


        detail = (

            f"Funnel: {actual}\n"
            f"Selection feedback: "
            f"{feedback['selection_feedback']['feedback_count']}\n"
            f"No-selection feedback: "
            f"{feedback['no_selection_feedback']['feedback_count']}\n"
            f"Hospitals: "
            f"{hospitals['hospital_count']}"
        )


        record(
            "Demo analytics consistency",
            passed,
            detail,
        )


    except Exception as error:

        record(
            "Demo analytics consistency",
            False,
            str(
                error
            ),
        )


# =========================================================
# Individual regression scripts
# =========================================================

def run_script_tests():

    print_header(
        "5. TRANSACTION REGRESSION TESTS"
    )


    for test in SCRIPT_TESTS:

        script_path = (
            BACKEND_DIR
            / test[
                "file"
            ]
        )


        if not script_path.exists():

            record(
                test[
                    "name"
                ],
                False,
                (
                    "Missing test file: "
                    f"{script_path.name}"
                ),
            )


            continue


        print()

        print(
            f"Running: {test['name']}"
        )


        try:

            result = subprocess.run(

                [
                    sys.executable,
                    script_path.name,
                ],

                cwd=
                    str(
                        BACKEND_DIR
                    ),

                capture_output=
                    True,

                text=
                    True,

                errors=
                    "replace",

                timeout=
                    180,
            )


            output = (

                result.stdout

                +

                result.stderr
            )


            passed = (

                result.returncode
                == 0

                and

                test[
                    "expected"
                ]
                in output
            )


            if passed:

                record(
                    test[
                        "name"
                    ],
                    True,
                    test[
                        "expected"
                    ],
                )


            else:

                # -----------------------------------------
                # 실패 시 출력 마지막 60줄 표시
                # -----------------------------------------

                lines = (
                    output.splitlines()
                )


                tail = "\n".join(
                    lines[
                        -60:
                    ]
                )


                record(
                    test[
                        "name"
                    ],
                    False,
                    tail,
                )


        except subprocess.TimeoutExpired:

            record(
                test[
                    "name"
                ],
                False,
                "Timed out after 180 seconds.",
            )


# =========================================================
# Frontend production build
# =========================================================

def frontend_build_check():

    print_header(
        "7. FRONTEND PRODUCTION BUILD"
    )


    npm = (

        shutil.which(
            "npm.cmd"
        )

        or

        shutil.which(
            "npm"
        )
    )


    if npm is None:

        record(
            "Frontend production build",
            False,
            "npm not found in PATH.",
        )


        return


    try:

        result = subprocess.run(

            [
                npm,
                "run",
                "build",
            ],

            cwd=
                str(
                    FRONTEND_DIR
                ),

            capture_output=
                True,

            text=
                True,

            errors=
                "replace",

            timeout=
                300,
        )


        output = (

            result.stdout

            +

            result.stderr
        )


        if (
            result.returncode
            == 0
        ):

            record(
                "Frontend production build",
                True,
                "npm run build exited with code 0.",
            )


        else:

            lines = (
                output.splitlines()
            )


            tail = "\n".join(
                lines[
                    -80:
                ]
            )


            record(
                "Frontend production build",
                False,
                tail,
            )


    except subprocess.TimeoutExpired:

        record(
            "Frontend production build",
            False,
            "Frontend build timed out.",
        )


# =========================================================
# Generic Python -c helper
# =========================================================

def run_python_check(
    name: str,
    code: str,
    expected: str,
):

    try:

        result = subprocess.run(

            [
                sys.executable,
                "-c",
                code,
            ],

            cwd=
                str(
                    BACKEND_DIR
                ),

            capture_output=
                True,

            text=
                True,

            errors=
                "replace",

            timeout=
                60,
        )


        output = (

            result.stdout

            +

            result.stderr
        )


        passed = (

            result.returncode
            == 0

            and

            expected
            in output
        )


        record(
            name,
            passed,
            (
                expected
                if passed
                else output
            ),
        )


    except subprocess.TimeoutExpired:

        record(
            name,
            False,
            "Python check timed out.",
        )


# =========================================================
# Final report
# =========================================================

def final_report():

    print_header(
        "FINAL REGRESSION RESULT"
    )


    passed_count = sum(

        1

        for result
        in results

        if result[
            "passed"
        ]
    )


    failed = [

        result

        for result
        in results

        if not result[
            "passed"
        ]
    ]


    print(
        "PASSED:",
        passed_count,
    )


    print(
        "TOTAL:",
        len(
            results
        ),
    )


    print()


    for result in results:

        icon = (
            "PASS"
            if result[
                "passed"
            ]
            else "FAIL"
        )


        print(
            f"{icon:4} | "
            f"{result['name']}"
        )


    print()


    if not failed:

        print(
            "ALL SYSTEM CHECKS: PASS"
        )


        return 0


    print(
        "ALL SYSTEM CHECKS: FAIL"
    )


    print()


    print(
        "Failed checks:"
    )


    for result in failed:

        print(
            "-",
            result[
                "name"
            ],
        )


    return 1


# =========================================================
# Main
# =========================================================

def main():

    print_header(
        "MODOODOC FULL REGRESSION SUITE"
    )


    print(
        "Python:",
        sys.executable,
    )


    print(
        "Backend:",
        BACKEND_DIR,
    )


    print(
        "Frontend:",
        FRONTEND_DIR,
    )


    temporary_server = None


    try:

        server_result = (
            ensure_fastapi()
        )


        if (
            server_result
            is False
        ):

            return 1


        temporary_server = (
            server_result
        )


        backend_import_check()


        mcp_registration_check()


        analytics_check(
            "4. ANALYTICS BASELINE CHECK"
        )


        run_script_tests()


        # -------------------------------------------------
        # Regression test들이 자기 데이터를 cleanup한 뒤
        # Demo dataset 숫자가 그대로 유지되는지 재확인
        # -------------------------------------------------

        analytics_check(
            "6. ANALYTICS POST-TEST CHECK"
        )


        frontend_build_check()


        return final_report()


    finally:

        if (
            temporary_server
            is not None
            and
            temporary_server
            is not False
        ):

            print()

            print(
                "Stopping temporary FastAPI server..."
            )


            temporary_server.terminate()


            try:

                temporary_server.wait(
                    timeout=10
                )


            except subprocess.TimeoutExpired:

                temporary_server.kill()


# =========================================================
# Execute
# =========================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )