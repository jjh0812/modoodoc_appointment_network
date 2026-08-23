# Appointment Transaction Network

병원마다 제각각인 의료 서비스·가격·예약 데이터를 표준화하고,  
사용자의 자연어 조건을 실제 예약 가능한 후보로 변환한 뒤  
검색 → 선택 → HOLD → 예약 확정까지 안전하게 처리하는 Backend / AI Transaction Prototype입니다.

> 모든 병원, 의사, 가격, 사용자 행동 데이터는 시스템 검증을 위해 생성한 **synthetic demo data**입니다.  
> 실제 환자 데이터나 실제 의료기관 데이터를 사용하지 않습니다.

---

## 1. What This Project Solves

실제 예약 시스템에서는 단순히 화면에 병원을 보여주는 것보다 다음 문제가 더 어렵습니다.

- 병원마다 가격과 서비스 데이터 형식이 다름
- 동일한 시술이 여러 이름으로 표현됨
- 사용자의 자연어 요청을 구조화된 검색 조건으로 바꿔야 함
- 실제 예약 가능 시간과 사용자 조건을 함께 비교해야 함
- 마지막 슬롯 하나에 여러 요청이 동시에 들어와도 중복 예약이 발생하면 안 됨
- AI가 retry해도 같은 예약이 여러 번 생성되면 안 됨
- 검색 이후 사용자가 무엇을 선택했고 왜 선택했는지 추적할 수 있어야 함

이 프로젝트는 이 문제를 하나의 transaction flow로 연결합니다.

```text
Heterogeneous Provider Data
        ↓
Raw Evidence
        ↓
Normalization / Reconciliation
        ↓
Canonical ProviderOffer
        ↓
Patient Intent
        ↓
Constraint Matching
        +
Availability
        ↓
Candidate Ranking
        ↓
SHOWN
        ↓
SELECTED
        ↓
HELD
        ↓
CONFIRMED
        ↓
Decision Analytics / Feedback
```

---

## 2. Architecture

```mermaid
flowchart TD
    A[Heterogeneous Provider Data] --> B[RawOfferEvidence]

    B --> C[Normalization]
    C --> D[Reconciliation]
    D --> E[Canonical ProviderOffer]

    U[Patient Natural Language Intent] --> F[Intent Normalization]

    E --> G[Constraint Matching]
    F --> G
    S[AppointmentSlot] --> G

    G --> H[CandidateMatch]
    H --> I[SHOWN]
    I --> J[SELECTED]

    J --> K[Slot HOLD]
    K --> L[Appointment CONFIRMED]

    I --> M[DecisionEvent]
    J --> M
    K --> M
    L --> M

    M --> N[Decision Analytics]
    O[DecisionFeedback] --> N

    P[MCP Tools] --> G
    P --> K
    P --> L
```

---

## 3. Data Normalization

병원 데이터가 항상 동일한 형태로 들어온다고 가정하지 않습니다.

Synthetic market seed에서는 같은 의미의 서비스를 일부러 다음과 같이 서로 다른 형식으로 생성합니다.

```text
JSON API
CSV
Free Text
Admin Format
Website HTML-like Text
Nested JSON
Legacy CSV
Sparse Text
Incomplete Admin Data
Conflicting Sources
```

예를 들어 동일한 canonical procedure가 원본에서는 다음처럼 표현될 수 있습니다.

```text
스마일라식
SMILE
스마일 프로
시력교정 스마일
SMILE LASIK
스마일 시력교정
```

Normalization / Reconciliation layer가 이를 표준화하여 다음 형태의 `ProviderOffer`로 변환합니다.

```text
procedure_code
price_min
price_max
confidence
normalization_status
provider_id
raw_evidence_id
```

검증된 synthetic dataset 기준:

```text
Hospitals                10
Providers                34
Raw Offer Evidence       38
Canonical ProviderOffer  28
Appointment Slots       170
```

Normalization 결과:

```text
Normalized Raw Evidence  28
Review Required          10
Canonical Offers         28
```

불확실하거나 충돌하는 데이터는 강제로 canonical data로 확정하지 않고 review 대상으로 남깁니다.

---

## 4. Patient Intent & Care Matching

사용자의 요청을 구조화된 `PatientIntent`로 저장합니다.

예:

```text
"강남에서 스마일 시력교정 받고 싶은데
 200만원 이하이고 오후 예약 가능한 곳"
```

구조화된 조건:

```text
procedure
region / district
preferred_date
time_window
budget
source
raw_query
```

그 후 다음 데이터를 함께 비교합니다.

```text
PatientIntent
      +
Canonical ProviderOffer
      +
Appointment Availability
      ↓
CandidateMatch
```

현재 matching score는 다음 조건 적합도를 나타냅니다.

```text
procedure match
district match
availability
budget fit
data confidence
```

`match_score`는 의료 품질 점수가 아니라 **사용자의 검색 조건에 대한 적합도**입니다.

---

## 5. Transaction-Safe Booking

검색 결과를 선택했다고 바로 예약을 생성하지 않습니다.

```text
AVAILABLE
   ↓
SELECTED
   ↓
HELD
   ↓
CONFIRMED
```

먼저 슬롯을 임시 확보한 후 사용자가 명시적으로 확인했을 때만 Appointment를 생성합니다.

PostgreSQL row-level locking을 사용하여 동일 슬롯에 여러 요청이 동시에 들어오는 상황을 제어합니다.

---

## 6. Concurrency Safety

가장 중요한 transaction test 중 하나는 다음 상황입니다.

```text
남은 AppointmentSlot = 1개

동시에 Confirm 요청 = 100개
```

검증 결과:

```text
100 concurrent HTTP requests
        ↓
100 successful idempotent responses
        ↓
Unique Appointment = 1
        ↓
Database Appointment = 1
```

즉 동시에 많은 요청이 들어와도 실제 예약은 정확히 하나만 생성됩니다.

---

## 7. Idempotency

AI agent나 외부 시스템은 timeout 또는 network retry 때문에 같은 요청을 다시 보낼 수 있습니다.

따라서 예약 확정 API는 `idempotency_key`를 사용합니다.

```text
Request #1
idempotency_key = abc123
        ↓
Appointment #1 생성

Request #2
idempotency_key = abc123
        ↓
기존 Appointment #1 반환
```

동일 key를 다른 HOLD에 재사용하는 경우에는 conflict로 차단합니다.

검증된 시나리오:

```text
Concurrent confirm             PASS
Expired HOLD confirm blocked   PASS
Idempotency retry              PASS
Idempotency key reuse blocked  PASS
```

---

## 8. Decision Graph

예약 성공 여부만 저장하지 않고 사용자의 decision lifecycle을 기록합니다.

```text
PatientIntent
    ↓
CandidateMatch
    ↓
DecisionEvent

SHOWN
SELECTED
HELD
CONFIRMED
```

이를 통해 다음과 같은 질문을 분석할 수 있습니다.

```text
검색한 사용자 중 몇 명에게 후보를 보여줬는가?
후보를 본 뒤 몇 명이 선택했는가?
선택 후 몇 명이 HOLD까지 갔는가?
HOLD 후 몇 명이 실제 예약했는가?
어떤 병원이 선택되고 어떤 병원이 선택되지 않았는가?
```

---

## 9. Decision Feedback

관찰된 행동과 사용자가 직접 말한 이유를 분리합니다.

```text
DecisionEvent
→ 사용자가 무엇을 했는가

DecisionFeedback
→ 사용자가 왜 그렇게 했다고 말했는가
```

Selection feedback 예:

```text
PRICE
AVAILABILITY
LOCATION
DATA_CONFIDENCE
OTHER
```

No-selection feedback 예:

```text
BUDGET_TOO_HIGH
TIME_NOT_MATCH
LOCATION_NOT_MATCH
INSUFFICIENT_INFORMATION
OTHER
```

Analytics에서 관찰된 차이는 causal reason으로 단정하지 않습니다.

---

## 10. Demo Analytics Dataset

Analytics UI와 API 검증을 위해 deterministic synthetic behavior dataset을 생성합니다.

```text
SEARCHED    30
   ↓
SHOWN       24
   ↓
SELECTED    10
   ↓
HELD        10
   ↓
CONFIRMED    5
```

Conversion:

```text
Search → Shown       80.0%
Shown → Selected     41.7%
Selected → Held     100.0%
Held → Confirmed     50.0%
Search → Confirmed   16.7%
```

Synthetic selection feedback:

```text
PRICE             50.0%
AVAILABILITY      40.0%
LOCATION          30.0%
DATA_CONFIDENCE   20.0%
```

Synthetic no-selection feedback:

```text
BUDGET_TOO_HIGH           50.0%
TIME_NOT_MATCH            37.5%
INSUFFICIENT_INFORMATION  25.0%
LOCATION_NOT_MATCH        12.5%
```

한 사용자가 복수 이유를 선택할 수 있으므로 feedback 비율 합계는 100%를 초과할 수 있습니다.

---

## 11. MCP / AI Integration

Backend transaction capability를 MCP tools로도 노출할 수 있습니다.

Local MCP tools:

```text
search_care_options
hold_care_option
confirm_appointment
```

Flow:

```text
Natural Language
      ↓
AI Agent
      ↓
MCP search_care_options
      ↓
Candidate IDs
      ↓
MCP hold_care_option
      ↓
Slot HOLD
      ↓
Explicit User Confirmation
      ↓
MCP confirm_appointment
```

`confirm_appointment`는 explicit confirmation 없이 바로 예약을 확정하지 않도록 설계했습니다.

별도의 public search-only MCP server도 있으며 외부 공개 환경에서는 search capability만 노출할 수 있습니다.

Remote MCP를 사용하려면 HTTPS endpoint와 `PUBLIC_MCP_URL` 설정이 필요합니다.

---

## 12. Operational Readiness

기능 동작뿐 아니라 운영 환경에서 필요한 기본적인 observability도 포함합니다.

### Liveness

```http
GET /health/live
```

FastAPI 프로세스가 요청을 처리할 수 있는지 확인합니다.

### Readiness

```http
GET /health/ready
```

PostgreSQL에 실제 `SELECT 1`을 실행하여 DB까지 사용할 수 있는지 확인합니다.

정상:

```json
{
  "status": "ready",
  "database": "ok"
}
```

DB 연결 불가 시 HTTP `503 Service Unavailable`을 반환합니다.

### Request ID

모든 HTTP 요청은 `X-Request-ID`를 가집니다.

클라이언트가 ID를 보내면 그대로 이어서 사용하고, 없으면 서버가 UUID를 생성합니다.

```text
Client
X-Request-ID: demo-request-001

        ↓

FastAPI

        ↓

Response
X-Request-ID: demo-request-001
```

### Structured Logging

각 요청을 JSON 형태로 기록합니다.

```json
{
  "event": "http_request",
  "request_id": "demo-request-001",
  "method": "GET",
  "path": "/health/ready",
  "status_code": 200,
  "duration_ms": 3.42
}
```

Request body와 query parameter는 request log에 저장하지 않습니다.

---

## 13. Docker

Docker Compose로 Backend와 PostgreSQL을 독립된 환경에서 실행할 수 있습니다.

```text
Docker Backend
      ↓
Docker Network
      ↓
Docker PostgreSQL
```

### Build & Start

```bash
docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
```

예상 상태:

```text
backend     Up
postgres    Up (healthy)
```

Health 확인:

```bash
curl http://127.0.0.1:8001/health/live
curl http://127.0.0.1:8001/health/ready
```

Docker PostgreSQL은 container 내부에서 `5432`를 사용하며 개발용 host port는 `5435`로 노출됩니다.

---

## 14. Demo Environment Bootstrap

새 PostgreSQL 환경에서도 전체 demo dataset을 다시 만들 수 있습니다.

Docker Backend가 실행 중일 때:

```bash
docker compose exec backend python bootstrap_demo.py
```

Bootstrap 내부 순서:

```text
seed_market.py
      ↓
normalization_apply.py
      ↓
seed_demo_analytics.py --apply
```

최종 목표:

```text
MARKET SEED: PASS
Offer normalization: PASS
Demo analytics seed: PASS

DEMO ENVIRONMENT BOOTSTRAP: PASS
```

Bootstrap은 기존 demo transaction data가 존재하는 환경에서도 다시 실행할 수 있도록 FK dependency 순서에 따라 데이터를 초기화합니다.

Database primary key 값은 재실행할 때 증가할 수 있으며, application logic은 특정 PK 값에 의존하지 않습니다.

---

## 15. Full Regression Suite

핵심 시스템을 한 명령으로 검사할 수 있습니다.

```bash
cd backend
python regression_suite.py
```

현재 검증 항목:

```text
FastAPI health
Backend core imports
MCP tool registration
Demo analytics baseline
Operational health / request tracing
Concurrent idempotency
Expired HOLD protection
Idempotency key reuse protection
Decision Feedback E2E
Analytics post-test consistency
Frontend production build
```

실제 검증 결과:

```text
PASSED: 11
TOTAL: 11

ALL SYSTEM CHECKS: PASS
```

Regression test 실행 전후에도 demo funnel은 유지됩니다.

```text
Before
30 → 24 → 10 → 10 → 5

Regression Tests

After
30 → 24 → 10 → 10 → 5
```

---

## 16. Local Environment

Python:

```text
Python 3.11
```

Backend dependencies:

```text
FastAPI
Uvicorn
SQLAlchemy
PostgreSQL / psycopg
Pydantic
python-dotenv
MCP Python SDK
OpenAI SDK
```

Frontend:

```text
Next.js
TypeScript
```

Database:

```text
PostgreSQL
```

---

## 17. Environment Variables

실제 secret은 `backend/.env`에 저장하고 Git에 commit하지 않습니다.

예제는:

```text
backend/.env.example
```

을 참고합니다.

```env
DATABASE_URL=postgresql+psycopg://modoodoc:YOUR_PASSWORD@127.0.0.1:5434/modoodoc

OPENAI_API_KEY=YOUR_OPENAI_API_KEY

PUBLIC_MCP_URL=https://YOUR_PUBLIC_MCP_URL
```

실제 API key나 실제 password를 `.env.example`에 저장하면 안 됩니다.

---

## 18. Main Backend APIs

```text
GET  /health/live
GET  /health/ready

GET  /providers/{provider_id}/availability

POST /care-options/search

POST /slots/{slot_id}/hold

POST /holds/{hold_id}/confirm

POST /decision-feedback/selection
POST /decision-feedback/no-selection

GET  /analytics/decision-funnel
GET  /analytics/hospitals
GET  /analytics/hospitals/{hospital_id}/decision-loss
GET  /analytics/decision-feedback-summary
GET  /analytics/hospitals/{hospital_id}/selection-reasons
```

---

## 19. Engineering Focus

이 프로젝트의 핵심은 단순한 예약 UI 구현이 아닙니다.

중점적으로 검증한 부분은 다음과 같습니다.

```text
Heterogeneous data normalization
Canonical data model
Evidence provenance
Constraint-based matching
Transaction lifecycle
PostgreSQL row locking
Concurrent request safety
Idempotent retries
Decision event modeling
Explicit user feedback
MCP tool integration
Operational health checks
Request tracing
Structured logging
Docker reproducibility
Automated regression testing
```

---

## 20. Disclaimer

본 프로젝트는 backend architecture와 transaction system을 검증하기 위한 prototype입니다.

- 모든 병원은 가상 병원입니다.
- 모든 의사는 가상 인물입니다.
- 모든 가격은 synthetic data입니다.
- 모든 사용자 행동 및 feedback은 demo dataset입니다.
- 의료적 품질 또는 치료 결과를 평가하지 않습니다.
- `constraint_match_score`는 의료 품질 점수가 아니라 검색 조건 적합도입니다.