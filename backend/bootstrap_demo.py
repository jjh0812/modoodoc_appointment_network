import subprocess
import sys

from pathlib import Path


# =========================================================
# Demo Environment Bootstrap
#
# 목적:
#
# 빈 PostgreSQL에서
#
# 1. Market seed
# 2. Offer normalization
# 3. Demo analytics behavior seed
#
# 를 순서대로 실행한다.
#
#
# 사용:
#
# python bootstrap_demo.py
#
# Docker:
#
# docker compose exec backend python bootstrap_demo.py
# =========================================================


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


STEPS = [
    {
        "name":
            "Market seed",

        "command": [
            sys.executable,
            "seed_market.py",
        ],

        "expected":
            "MARKET SEED: PASS",
    },

    {
        "name":
            "Offer normalization",

        "command": [
            sys.executable,
            "normalization_apply.py",
        ],

        "expected":
            "CANONICAL PROVIDER OFFERS: 28",
    },

    {
        "name":
            "Demo analytics seed",

        "command": [
            sys.executable,
            "seed_demo_analytics.py",
            "--apply",
        ],

        "expected":
            "DEMO ANALYTICS DATASET: PASS",
    },
]


def run_step(
    name: str,
    command: list[str],
    expected: str,
):

    print()

    print(
        "=" * 60
    )

    print(
        name.upper()
    )

    print(
        "=" * 60
    )


    result = subprocess.run(
        command,
        cwd=str(
            BACKEND_DIR
        ),
        capture_output=True,
        text=True,
        errors="replace",
    )


    output = (
        result.stdout
        +
        result.stderr
    )


    print(
        output
    )


    if (
        result.returncode
        != 0
    ):

        raise RuntimeError(
            (
                f"{name} failed "
                f"with exit code "
                f"{result.returncode}"
            )
        )


    if (
        expected
        not in output
    ):

        raise RuntimeError(
            (
                f"{name} did not produce "
                f"expected result: "
                f"{expected}"
            )
        )


    print(
        f"{name}: PASS"
    )


def main():

    print()

    print(
        "============================================================"
    )

    print(
        "DEMO ENVIRONMENT BOOTSTRAP"
    )

    print(
        "============================================================"
    )


    for step in STEPS:

        run_step(
            name=
                step[
                    "name"
                ],

            command=
                step[
                    "command"
                ],

            expected=
                step[
                    "expected"
                ],
        )


    print()

    print(
        "============================================================"
    )

    print(
        "DEMO ENVIRONMENT BOOTSTRAP: PASS"
    )

    print(
        "============================================================"
    )


if __name__ == "__main__":

    main()