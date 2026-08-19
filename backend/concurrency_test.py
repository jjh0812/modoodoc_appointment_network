import json

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from urllib.error import HTTPError
from urllib.request import (
    Request,
    urlopen,
)


# =========================================================
# 테스트 설정
# =========================================================

REQUEST_COUNT = 100

URL = (
    "http://127.0.0.1:8001"
    "/slots/1/hold"
)


# =========================================================
# 모든 요청을 최대한 같은 순간에 출발시키기 위한 Barrier
# =========================================================

start_barrier = Barrier(
    REQUEST_COUNT
)


# =========================================================
# HOLD 요청 하나 보내기
# =========================================================

def send_hold_request(
    request_number: int,
):

    body = {
        "source": (
            f"concurrency-test-{request_number}"
        )
    }

    data = json.dumps(
        body
    ).encode("utf-8")


    request = Request(
        URL,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )


    # -----------------------------------------------------
    # 모든 thread가 여기까지 준비될 때까지 기다림
    #
    # 20개가 모두 준비되면
    # 거의 동시에 아래 HTTP 요청 실행
    # -----------------------------------------------------

    start_barrier.wait()


    try:

        with urlopen(
            request,
            timeout=30,
        ) as response:

            response_body = (
                response
                .read()
                .decode("utf-8")
            )

            return (
                response.status,
                response_body,
            )


    except HTTPError as error:

        response_body = (
            error
            .read()
            .decode("utf-8")
        )

        return (
            error.code,
            response_body,
        )


    except Exception as error:

        return (
            "ERROR",
            str(error),
        )


# =========================================================
# 20개 요청 동시에 실행
# =========================================================

with ThreadPoolExecutor(
    max_workers=REQUEST_COUNT
) as executor:

    results = list(
        executor.map(
            send_hold_request,
            range(
                1,
                REQUEST_COUNT + 1,
            ),
        )
    )


# =========================================================
# 결과 집계
# =========================================================

success_count = sum(
    1
    for status, _ in results
    if status == 200
)

conflict_count = sum(
    1
    for status, _ in results
    if status == 409
)

other_count = (
    REQUEST_COUNT
    - success_count
    - conflict_count
)


print()
print("========================================")
print("CONCURRENCY TEST RESULT")
print("========================================")

print(
    "TOTAL REQUESTS:",
    REQUEST_COUNT,
)

print(
    "200 SUCCESS:",
    success_count,
)

print(
    "409 CONFLICT:",
    conflict_count,
)

print(
    "OTHER:",
    other_count,
)


# =========================================================
# 누가 HOLD에 성공했는지 출력
# =========================================================

for status, body in results:

    if status == 200:

        print()
        print(
            "WINNING REQUEST:"
        )

        print(
            body
        )