import json
import logging
import time
import uuid

from fastapi import (
    Request,
)

from starlette.middleware.base import (
    BaseHTTPMiddleware,
)


# =========================================================
# Structured Request Logger
#
# 일반 문장 로그가 아니라
# JSON 형태로 요청 정보를 남긴다.
#
# 예:
#
# {
#     "event": "http_request",
#     "request_id": "...",
#     "method": "GET",
#     "path": "/health/ready",
#     "status_code": 200,
#     "duration_ms": 4.21
# }
# =========================================================

request_logger = logging.getLogger(
    "app.request"
)


if not request_logger.handlers:

    handler = logging.StreamHandler()

    handler.setFormatter(
        logging.Formatter(
            "%(message)s"
        )
    )

    request_logger.addHandler(
        handler
    )


request_logger.setLevel(
    logging.INFO
)

request_logger.propagate = False


# =========================================================
# Request Context Middleware
#
# 모든 HTTP 요청에:
#
# 1. Request ID 생성 / 전달
# 2. 처리 시간 측정
# 3. JSON Structured Log 기록
# 4. Response Header에 Request ID 반환
#
# 을 수행한다.
# =========================================================

class RequestContextMiddleware(
    BaseHTTPMiddleware
):

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):

        # -------------------------------------------------
        # 1. 기존 Request ID 확인
        #
        # 외부 시스템이 이미 X-Request-ID를 보냈다면
        # 그 ID를 이어서 사용한다.
        #
        # 없으면 서버가 UUID를 새로 만든다.
        # -------------------------------------------------

        request_id = (
            request.headers.get(
                "X-Request-ID"
            )
        )


        if (
            not request_id
            or
            len(request_id) > 128
        ):

            request_id = str(
                uuid.uuid4()
            )


        # -------------------------------------------------
        # 2. 다른 Router에서도 사용할 수 있도록
        # request.state에 저장
        # -------------------------------------------------

        request.state.request_id = (
            request_id
        )


        # -------------------------------------------------
        # 3. 처리 시간 측정 시작
        # -------------------------------------------------

        started_at = (
            time.perf_counter()
        )


        status_code = 500


        try:

            response = await call_next(
                request
            )


            status_code = (
                response.status_code
            )


            # ---------------------------------------------
            # 클라이언트도 Request ID를 알 수 있도록
            # Response Header에 반환
            # ---------------------------------------------

            response.headers[
                "X-Request-ID"
            ] = request_id


            return response


        finally:

            duration_ms = round(
                (
                    time.perf_counter()
                    -
                    started_at
                )
                * 1000,
                2,
            )


            # ---------------------------------------------
            # Query parameter나 Request body는
            # 로그에 기록하지 않는다.
            #
            # 의료/개인정보 같은 민감 정보가
            # 로그에 섞이는 것을 방지한다.
            # ---------------------------------------------

            log_record = {

                "event":
                    "http_request",

                "request_id":
                    request_id,

                "method":
                    request.method,

                "path":
                    request.url.path,

                "status_code":
                    status_code,

                "duration_ms":
                    duration_ms,
            }


            request_logger.info(
                json.dumps(
                    log_record,
                    ensure_ascii=False,
                )
            )