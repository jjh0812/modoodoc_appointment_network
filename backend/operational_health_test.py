import json

from urllib.request import (
    Request,
    urlopen,
)


BASE_URL = (
    "http://127.0.0.1:8001"
)


REQUEST_ID = (
    "regression-request-001"
)


# =========================================================
# HTTP GET helper
# =========================================================

def get(
    path: str,
    headers: dict | None = None,
):

    request = Request(
        BASE_URL + path,
        headers=headers or {},
        method="GET",
    )


    with urlopen(
        request,
        timeout=5,
    ) as response:

        body = json.loads(
            response
            .read()
            .decode(
                "utf-8"
            )
        )


        return (
            response.status,
            response.headers,
            body,
        )


# =========================================================
# 1. Liveness
# =========================================================

live_status, _, live_body = get(
    "/health/live"
)


if live_status != 200:

    raise RuntimeError(
        (
            "Expected /health/live "
            f"HTTP 200, got {live_status}"
        )
    )


if (
    live_body.get(
        "status"
    )
    != "ok"
):

    raise RuntimeError(
        (
            "Unexpected liveness body: "
            f"{live_body}"
        )
    )


print(
    "LIVENESS: PASS"
)


# =========================================================
# 2. Readiness
#
# PostgreSQL SELECT 1까지 성공해야 한다.
# =========================================================

ready_status, _, ready_body = get(
    "/health/ready"
)


if ready_status != 200:

    raise RuntimeError(
        (
            "Expected /health/ready "
            f"HTTP 200, got {ready_status}"
        )
    )


if (
    ready_body.get(
        "status"
    )
    != "ready"
):

    raise RuntimeError(
        (
            "Unexpected readiness status: "
            f"{ready_body}"
        )
    )


if (
    ready_body.get(
        "database"
    )
    != "ok"
):

    raise RuntimeError(
        (
            "Database is not ready: "
            f"{ready_body}"
        )
    )


print(
    "READINESS: PASS"
)


# =========================================================
# 3. Request ID round trip
#
# Client
# X-Request-ID: regression-request-001
#
#       ↓
#
# FastAPI Middleware
#
#       ↓
#
# Response
# X-Request-ID: regression-request-001
# =========================================================

request_status, request_headers, _ = get(

    "/health/ready",

    headers={
        "X-Request-ID":
            REQUEST_ID,
    },
)


if request_status != 200:

    raise RuntimeError(
        (
            "Request ID test returned "
            f"HTTP {request_status}"
        )
    )


returned_request_id = (
    request_headers.get(
        "X-Request-ID"
    )
)


if (
    returned_request_id
    != REQUEST_ID
):

    raise RuntimeError(
        (
            "Request ID mismatch. "
            f"Sent={REQUEST_ID}, "
            f"Returned={returned_request_id}"
        )
    )


print(
    "REQUEST ID ROUND TRIP: PASS"
)


# =========================================================
# Final
# =========================================================

print(
    "OPERATIONAL HEALTH: PASS"
)