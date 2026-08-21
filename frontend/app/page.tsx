"use client";

import {
  useEffect,
  useState,
} from "react";


const API_BASE =
  "http://127.0.0.1:8001";


// =========================================================
// Types
// =========================================================

type CareOptionCandidate = {
  candidate_match_id: number;

  provider_id: number;
  provider_name: string;

  hospital_id: number;
  hospital_name: string;
  district: string;

  offer_id: number;

  procedure_code: string;
  procedure_name: string;

  price_min: number | null;
  price_max: number | null;

  earliest_slot_id: number;
  earliest_slot_time: string;

  constraint_match_score: number;

  budget_status: string;

  data_confidence: number;

  reasons: string[];
};


type CareOptionsSearchResponse = {
  intent_id: number;

  candidates: CareOptionCandidate[];
};


type SlotHold = {
  id: number;

  slot_id: number;

  source: string;

  expires_at: string;

  status: string;
};


type Appointment = {
  id: number;

  slot_id: number;

  hold_id: number;

  source: string;

  idempotency_key: string;

  status: string;

  created_at: string;
};


// =========================================================
// 가격 표시
// =========================================================

function formatPrice(
  value: number | null
) {

  if (value === null) {
    return "미확인";
  }


  return (
    `${Math.floor(value / 10000)}만원`
  );
}


// =========================================================
// 가격 범위 표시
// =========================================================

function formatPriceRange(
  priceMin: number | null,
  priceMax: number | null,
) {

  if (
    priceMin === null
    &&
    priceMax === null
  ) {

    return "가격 확인 필요";
  }


  if (
    priceMin !== null
    &&
    priceMax === null
  ) {

    return (
      `${formatPrice(priceMin)}부터`
    );
  }


  return (
    `${formatPrice(priceMin)} ~ ${formatPrice(priceMax)}`
  );
}


// =========================================================
// 예약시간 표시
// =========================================================

function formatSlotTime(
  value: string
) {

  const date =
    new Date(value);


  return new Intl.DateTimeFormat(
    "ko-KR",
    {
      month: "long",
      day: "numeric",
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }
  ).format(date);
}


// =========================================================
// HOLD expires_at은 UTC로 저장됨
// =========================================================

function getUtcTime(
  value: string
) {

  const hasTimezone =
    value.endsWith("Z")
    ||
    /[+-]\d\d:\d\d$/.test(value);


  const normalized =
    hasTimezone
      ? value
      : `${value}Z`;


  return new Date(
    normalized
  ).getTime();
}


// =========================================================
// Budget status 한글 표시
// =========================================================

function budgetStatusLabel(
  value: string
) {

  if (value === "WITHIN_BUDGET") {
    return "예산 범위 내";
  }


  if (value === "PARTIAL_MATCH") {
    return "예산 일부 일치";
  }


  if (value === "NOT_SPECIFIED") {
    return "예산 미지정";
  }


  return value;
}


// =========================================================
// Main
// =========================================================

export default function Home() {

  // =======================================================
  // Patient Intent
  // =======================================================

  const [
    query,
    setQuery,
  ] = useState(
    "8월 22일 오후 강남에서 200만원 정도로 스마일 시력교정 검진 가능한 곳 찾아줘"
  );


  const [
    district,
    setDistrict,
  ] = useState(
    "강남"
  );


  const [
    preferredDate,
    setPreferredDate,
  ] = useState(
    "2026-08-22"
  );


  const [
    timeWindow,
    setTimeWindow,
  ] = useState(
    "AFTERNOON"
  );


  const [
    budgetMax,
    setBudgetMax,
  ] = useState(
    2000000
  );


  // =======================================================
  // Search 결과
  // =======================================================

  const [
    intentId,
    setIntentId,
  ] = useState<number | null>(
    null
  );


  const [
    candidates,
    setCandidates,
  ] = useState<CareOptionCandidate[]>(
    []
  );


  const [
    selectedCandidate,
    setSelectedCandidate,
  ] = useState<CareOptionCandidate | null>(
    null
  );


  // =======================================================
  // Transaction
  // =======================================================

  const [
    hold,
    setHold,
  ] = useState<SlotHold | null>(
    null
  );


  const [
    appointment,
    setAppointment,
  ] = useState<Appointment | null>(
    null
  );


  const [
    idempotencyKey,
    setIdempotencyKey,
  ] = useState<string | null>(
    null
  );


  const [
    secondsLeft,
    setSecondsLeft,
  ] = useState(0);


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  // =======================================================
  // HOLD countdown
  // =======================================================

  useEffect(
    () => {

      if (
        !hold
        ||
        hold.status !== "ACTIVE"
      ) {

        setSecondsLeft(0);

        return;
      }


      const updateCountdown =
        () => {

          const remaining =
            Math.max(
              0,

              Math.floor(
                (
                  getUtcTime(
                    hold.expires_at
                  )
                  -
                  Date.now()
                )
                / 1000
              )
            );


          setSecondsLeft(
            remaining
          );
        };


      updateCountdown();


      const timer =
        window.setInterval(
          updateCountdown,
          1000
        );


      return () => {

        window.clearInterval(
          timer
        );
      };

    },

    [hold]
  );


  // =======================================================
  // 1. Care Option Search
  // =======================================================

  async function searchCareOptions() {

    if (
      hold
      &&
      hold.status === "ACTIVE"
      &&
      secondsLeft > 0
    ) {

      setError(
        "현재 ACTIVE HOLD가 있습니다. 예약을 확정하거나 HOLD가 만료된 뒤 다시 검색해주세요."
      );

      return;
    }


    setLoading(true);

    setError("");

    setCandidates([]);

    setIntentId(null);

    setSelectedCandidate(null);

    setHold(null);

    setAppointment(null);

    setIdempotencyKey(null);


    try {

      const response =
        await fetch(
          `${API_BASE}/care-options/search`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                procedure_code:
                  "VISION_CORRECTION_SMILE",

                district:
                  district,

                preferred_date:
                  preferredDate,

                time_window:
                  timeWindow,

                budget_max:
                  budgetMax,

                source:
                  "AI_SIMULATOR",

                raw_query:
                  query,

                limit:
                  3,
              }
            ),
          }
        );


      if (!response.ok) {

        const body =
          await response.json();


        throw new Error(
          body.detail
          ??
          "후보 검색에 실패했습니다."
        );
      }


      const data:
        CareOptionsSearchResponse =
        await response.json();


      setIntentId(
        data.intent_id
      );


      setCandidates(
        data.candidates
      );

    }

    catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "알 수 없는 오류가 발생했습니다."
      );

    }

    finally {

      setLoading(false);
    }
  }


  // =======================================================
  // 2. Candidate 선택 → HOLD
  // =======================================================

  async function selectCandidate(
    candidate: CareOptionCandidate
  ) {

    setLoading(true);

    setError("");


    try {

      const response =
        await fetch(
          (
            `${API_BASE}`
            +
            `/slots/${candidate.earliest_slot_id}/hold`
          ),
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                source:
                  "AI_SIMULATOR",

                candidate_match_id:
                  candidate.candidate_match_id,
              }
            ),
          }
        );


      if (!response.ok) {

        const body =
          await response.json();


        throw new Error(
          body.detail
          ??
          "슬롯 HOLD에 실패했습니다."
        );
      }


      const holdData:
        SlotHold =
        await response.json();


      setSelectedCandidate(
        candidate
      );


      setHold(
        holdData
      );


      setAppointment(
        null
      );


      // ---------------------------------------------------
      // 이 HOLD의 모든 retry에서 같은 key 사용
      // ---------------------------------------------------

      setIdempotencyKey(
        crypto.randomUUID()
      );

    }

    catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "알 수 없는 오류가 발생했습니다."
      );

    }

    finally {

      setLoading(false);
    }
  }


  // =======================================================
  // 3. CONFIRM
  // =======================================================

  async function confirmAppointment() {

    if (
      !hold
      ||
      !idempotencyKey
    ) {

      return;
    }


    setLoading(true);

    setError("");


    try {

      const response =
        await fetch(
          (
            `${API_BASE}`
            +
            `/holds/${hold.id}/confirm`
          ),
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                idempotency_key:
                  idempotencyKey,
              }
            ),
          }
        );


      if (!response.ok) {

        const body =
          await response.json();


        throw new Error(
          body.detail
          ??
          "예약 확정에 실패했습니다."
        );
      }


      const data:
        Appointment =
        await response.json();


      setAppointment(
        data
      );


      setHold(
        currentHold =>
          currentHold
            ? {
                ...currentHold,
                status: "CONFIRMED",
              }
            : null
      );


      setSecondsLeft(
        0
      );

    }

    catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "알 수 없는 오류가 발생했습니다."
      );

    }

    finally {

      setLoading(false);
    }
  }


  // =======================================================
  // UI
  // =======================================================

  return (

    <main
      className="
        min-h-screen
        bg-slate-50
        px-6
        py-10
        text-slate-900
      "
    >

      <div
        className="
          mx-auto
          max-w-7xl
        "
      >

        {/* =================================================
            Header
        ================================================= */}

        <header
          className="
            mb-9
          "
        >

          <div
            className="
              mb-3
              text-sm
              font-bold
              tracking-wide
              text-blue-600
            "
          >
            MODOODOC EXECUTABLE DECISION NETWORK
          </div>


          <h1
            className="
              text-4xl
              font-bold
              tracking-tight
            "
          >
            AI Care Decision Simulator
          </h1>


          <p
            className="
              mt-4
              max-w-3xl
              text-slate-600
            "
          >
            환자의 조건을 canonical intent로 변환하고,
            정규화된 병원 Offer와 실제 Availability를
            비교한 뒤 선택된 후보를 안전하게
            HOLD → CONFIRM하는 프로토타입입니다.
          </p>

        </header>


        <div
          className="
            grid
            gap-6
            xl:grid-cols-[1.15fr_0.85fr]
          "
        >

          {/* =================================================
              LEFT
          ================================================= */}

          <section
            className="
              rounded-2xl
              border
              border-slate-200
              bg-white
              p-6
              shadow-sm
            "
          >

            <h2
              className="
                text-xl
                font-bold
              "
            >
              Patient Intent
            </h2>


            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              현재 자연어 자체를 LLM이 파싱하는 단계는
              아직 연결하지 않았으며, 아래 구조화 조건과
              원문을 함께 backend에 전달합니다.
            </p>


            {/* QUERY */}

            <textarea
              value={query}

              onChange={
                event =>
                  setQuery(
                    event.target.value
                  )
              }

              className="
                mt-5
                min-h-24
                w-full
                resize-none
                rounded-xl
                border
                border-slate-300
                p-4
                outline-none
                focus:border-blue-500
              "
            />


            {/* CONSTRAINTS */}

            <div
              className="
                mt-4
                grid
                gap-3
                md:grid-cols-2
              "
            >

              <label
                className="
                  text-sm
                  font-semibold
                "
              >
                지역

                <input
                  value={district}

                  onChange={
                    event =>
                      setDistrict(
                        event.target.value
                      )
                  }

                  className="
                    mt-2
                    w-full
                    rounded-xl
                    border
                    border-slate-300
                    px-4
                    py-3
                    font-normal
                  "
                />

              </label>


              <label
                className="
                  text-sm
                  font-semibold
                "
              >
                날짜

                <input
                  type="date"

                  value={preferredDate}

                  onChange={
                    event =>
                      setPreferredDate(
                        event.target.value
                      )
                  }

                  className="
                    mt-2
                    w-full
                    rounded-xl
                    border
                    border-slate-300
                    px-4
                    py-3
                    font-normal
                  "
                />

              </label>


              <label
                className="
                  text-sm
                  font-semibold
                "
              >
                시간대

                <select
                  value={timeWindow}

                  onChange={
                    event =>
                      setTimeWindow(
                        event.target.value
                      )
                  }

                  className="
                    mt-2
                    w-full
                    rounded-xl
                    border
                    border-slate-300
                    px-4
                    py-3
                    font-normal
                  "
                >
                  <option value="MORNING">
                    오전
                  </option>

                  <option value="AFTERNOON">
                    오후
                  </option>

                  <option value="EVENING">
                    저녁
                  </option>

                  <option value="ANY">
                    상관없음
                  </option>
                </select>

              </label>


              <label
                className="
                  text-sm
                  font-semibold
                "
              >
                최대 예산

                <input
                  type="number"

                  value={budgetMax}

                  onChange={
                    event =>
                      setBudgetMax(
                        Number(
                          event.target.value
                        )
                      )
                  }

                  className="
                    mt-2
                    w-full
                    rounded-xl
                    border
                    border-slate-300
                    px-4
                    py-3
                    font-normal
                  "
                />

              </label>

            </div>


            <button
              onClick={
                searchCareOptions
              }

              disabled={loading}

              className="
                mt-5
                w-full
                rounded-xl
                bg-slate-950
                px-5
                py-3
                font-bold
                text-white
                transition
                hover:bg-slate-800
                disabled:opacity-50
              "
            >
              {
                loading
                  ? "처리 중..."
                  : "조건에 맞는 실행 가능한 후보 찾기"
              }
            </button>


            {/* INTENT RESULT */}

            {
              intentId !== null
              &&
              (
                <div
                  className="
                    mt-5
                    rounded-xl
                    bg-blue-50
                    p-4
                    text-sm
                    text-blue-900
                  "
                >
                  PatientIntent #{intentId} 생성
                  · 입력 지역 "{district}"는 backend의
                  Intent Normalization을 거쳐 검색됩니다.
                </div>
              )
            }


            {/* ERROR */}

            {
              error
              &&
              (
                <div
                  className="
                    mt-5
                    rounded-xl
                    bg-red-50
                    p-4
                    text-sm
                    text-red-700
                  "
                >
                  {error}
                </div>
              )
            }


            {/* =================================================
                CANDIDATES
            ================================================= */}

            {
              intentId !== null
              &&
              (
                <div
                  className="
                    mt-7
                  "
                >

                  <div
                    className="
                      mb-4
                      flex
                      items-end
                      justify-between
                    "
                  >

                    <div>

                      <h2
                        className="
                          text-xl
                          font-bold
                        "
                      >
                        실행 가능한 후보
                      </h2>


                      <p
                        className="
                          mt-1
                          text-sm
                          text-slate-500
                        "
                      >
                        의료 품질 순위가 아니라
                        사용자가 지정한 조건과의 일치도입니다.
                      </p>

                    </div>


                    <div
                      className="
                        text-sm
                        text-slate-400
                      "
                    >
                      {candidates.length} candidates
                    </div>

                  </div>


                  {
                    candidates.length === 0
                      ? (
                          <div
                            className="
                              rounded-xl
                              border
                              border-dashed
                              border-slate-300
                              p-8
                              text-center
                              text-slate-500
                            "
                          >
                            현재 조건에 맞는 실행 가능한
                            후보가 없습니다.
                          </div>
                        )

                      : (
                          <div
                            className="
                              space-y-4
                            "
                          >

                            {
                              candidates.map(
                                (
                                  candidate,
                                  index,
                                ) => {

                                  const isSelected =
                                    selectedCandidate
                                      ?.candidate_match_id
                                    ===
                                    candidate.candidate_match_id;


                                  return (

                                    <div
                                      key={
                                        candidate
                                          .candidate_match_id
                                      }

                                      className={`
                                        rounded-2xl
                                        border
                                        p-5
                                        transition

                                        ${
                                          isSelected
                                            ? "border-blue-500 bg-blue-50"
                                            : "border-slate-200 bg-white"
                                        }
                                      `}
                                    >

                                      <div
                                        className="
                                          flex
                                          gap-4
                                        "
                                      >

                                        {/* RANK */}

                                        <div
                                          className="
                                            flex
                                            h-10
                                            w-10
                                            shrink-0
                                            items-center
                                            justify-center
                                            rounded-full
                                            bg-slate-950
                                            font-bold
                                            text-white
                                          "
                                        >
                                          {index + 1}
                                        </div>


                                        <div
                                          className="
                                            min-w-0
                                            flex-1
                                          "
                                        >

                                          <div
                                            className="
                                              flex
                                              flex-wrap
                                              items-start
                                              justify-between
                                              gap-3
                                            "
                                          >

                                            <div>

                                              <div
                                                className="
                                                  text-lg
                                                  font-bold
                                                "
                                              >
                                                {
                                                  candidate
                                                    .hospital_name
                                                }
                                              </div>


                                              <div
                                                className="
                                                  mt-1
                                                  text-sm
                                                  text-slate-600
                                                "
                                              >
                                                {
                                                  candidate
                                                    .provider_name
                                                }
                                                {" · "}
                                                {
                                                  candidate
                                                    .procedure_name
                                                }
                                              </div>

                                            </div>


                                            <div
                                              className="
                                                rounded-full
                                                bg-slate-100
                                                px-3
                                                py-1
                                                text-sm
                                                font-bold
                                              "
                                            >
                                              조건 일치{" "}
                                              {
                                                candidate
                                                  .constraint_match_score
                                              }
                                            </div>

                                          </div>


                                          {/* CORE DATA */}

                                          <div
                                            className="
                                              mt-4
                                              grid
                                              gap-3
                                              sm:grid-cols-3
                                            "
                                          >

                                            <div
                                              className="
                                                rounded-xl
                                                bg-slate-50
                                                p-3
                                              "
                                            >
                                              <div
                                                className="
                                                  text-xs
                                                  text-slate-400
                                                "
                                              >
                                                예상 가격
                                              </div>

                                              <div
                                                className="
                                                  mt-1
                                                  font-bold
                                                "
                                              >
                                                {
                                                  formatPriceRange(
                                                    candidate
                                                      .price_min,

                                                    candidate
                                                      .price_max,
                                                  )
                                                }
                                              </div>
                                            </div>


                                            <div
                                              className="
                                                rounded-xl
                                                bg-slate-50
                                                p-3
                                              "
                                            >
                                              <div
                                                className="
                                                  text-xs
                                                  text-slate-400
                                                "
                                              >
                                                가장 빠른 슬롯
                                              </div>

                                              <div
                                                className="
                                                  mt-1
                                                  font-bold
                                                "
                                              >
                                                {
                                                  formatSlotTime(
                                                    candidate
                                                      .earliest_slot_time
                                                  )
                                                }
                                              </div>
                                            </div>


                                            <div
                                              className="
                                                rounded-xl
                                                bg-slate-50
                                                p-3
                                              "
                                            >
                                              <div
                                                className="
                                                  text-xs
                                                  text-slate-400
                                                "
                                              >
                                                데이터 Confidence
                                              </div>

                                              <div
                                                className="
                                                  mt-1
                                                  font-bold
                                                "
                                              >
                                                {
                                                  candidate
                                                    .data_confidence
                                                    .toFixed(2)
                                                }
                                              </div>
                                            </div>

                                          </div>


                                          {/* BUDGET */}

                                          <div
                                            className="
                                              mt-4
                                            "
                                          >

                                            <span
                                              className={`
                                                inline-flex
                                                rounded-full
                                                px-3
                                                py-1
                                                text-xs
                                                font-bold

                                                ${
                                                  candidate
                                                    .budget_status
                                                  ===
                                                  "WITHIN_BUDGET"

                                                    ? "bg-emerald-100 text-emerald-700"

                                                    : "bg-amber-100 text-amber-700"
                                                }
                                              `}
                                            >
                                              {
                                                budgetStatusLabel(
                                                  candidate
                                                    .budget_status
                                                )
                                              }
                                            </span>

                                          </div>


                                          {/* REASONS */}

                                          <div
                                            className="
                                              mt-4
                                              rounded-xl
                                              bg-slate-50
                                              p-4
                                            "
                                          >

                                            <div
                                              className="
                                                mb-2
                                                text-xs
                                                font-bold
                                                uppercase
                                                tracking-wide
                                                text-slate-400
                                              "
                                            >
                                              왜 이 후보가 나왔나
                                            </div>


                                            <ul
                                              className="
                                                space-y-1
                                                text-sm
                                                text-slate-600
                                              "
                                            >
                                              {
                                                candidate
                                                  .reasons
                                                  .map(
                                                    reason => (

                                                      <li
                                                        key={reason}
                                                      >
                                                        ✓ {reason}
                                                      </li>

                                                    )
                                                  )
                                              }
                                            </ul>

                                          </div>


                                          {/* SELECT */}

                                          <button
                                            onClick={
                                              () =>
                                                selectCandidate(
                                                  candidate
                                                )
                                            }

                                            disabled={
                                              loading
                                              ||
                                              (
                                                hold !== null
                                                &&
                                                hold.status
                                                === "ACTIVE"
                                              )
                                              ||
                                              appointment !== null
                                            }

                                            className="
                                              mt-4
                                              w-full
                                              rounded-xl
                                              bg-blue-600
                                              px-4
                                              py-3
                                              font-bold
                                              text-white
                                              hover:bg-blue-500
                                              disabled:cursor-not-allowed
                                              disabled:opacity-40
                                            "
                                          >
                                            {
                                              isSelected
                                                ? "선택됨 · HOLD 완료"
                                                : "이 후보 선택하고 HOLD"
                                            }
                                          </button>

                                        </div>

                                      </div>

                                    </div>

                                  );
                                }
                              )
                            }

                          </div>
                        )
                  }

                </div>
              )
            }

          </section>


          {/* =================================================
              RIGHT — TRANSACTION
          ================================================= */}

          <aside
            className="
              h-fit
              rounded-2xl
              border
              border-slate-200
              bg-white
              p-6
              shadow-sm
            "
          >

            <h2
              className="
                text-xl
                font-bold
              "
            >
              Transaction Graph
            </h2>


            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              이번 환자 의사결정이 실제 예약까지
              어떻게 이어지는지 보여줍니다.
            </p>


            {/* SHOWN */}

            <div
              className="
                mt-6
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-bold
                  text-slate-400
                "
              >
                STEP 1
              </div>


              <div
                className="
                  mt-1
                  font-bold
                "
              >
                SHOWN
              </div>


              <div
                className="
                  mt-2
                  text-sm
                  text-slate-600
                "
              >
                {
                  intentId
                    ? (
                        `${candidates.length}개의 후보를 PatientIntent #${intentId}에 표시`
                      )
                    : (
                        "아직 후보 검색 전입니다."
                      )
                }
              </div>

            </div>


            {/* SELECTED */}

            <div
              className="
                mt-3
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-bold
                  text-slate-400
                "
              >
                STEP 2
              </div>


              <div
                className="
                  mt-1
                  font-bold
                "
              >
                SELECTED
              </div>


              {
                selectedCandidate
                  ? (
                      <div
                        className="
                          mt-2
                          text-sm
                          text-slate-600
                        "
                      >
                        Candidate #
                        {
                          selectedCandidate
                            .candidate_match_id
                        }

                        <br />

                        {
                          selectedCandidate
                            .hospital_name
                        }

                        {" · "}

                        {
                          selectedCandidate
                            .provider_name
                        }
                      </div>
                    )

                  : (
                      <div
                        className="
                          mt-2
                          text-sm
                          text-slate-400
                        "
                      >
                        아직 선택된 후보가 없습니다.
                      </div>
                    )
              }

            </div>


            {/* HOLD */}

            <div
              className="
                mt-3
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-bold
                  text-slate-400
                "
              >
                STEP 3
              </div>


              <div
                className="
                  mt-1
                  font-bold
                "
              >
                HELD
              </div>


              {
                hold
                  ? (
                      <div
                        className="
                          mt-3
                        "
                      >

                        <div
                          className="
                            text-sm
                            font-bold
                            text-emerald-700
                          "
                        >
                          Hold #{hold.id} {hold.status}
                        </div>


                        {
                          hold.status === "ACTIVE"
                            ? (
                                <>
                                  <div
                                    className="
                                      mt-2
                                      text-4xl
                                      font-bold
                                    "
                                  >
                                    {
                                      Math.floor(
                                        secondsLeft / 60
                                      )
                                    }
                                    :
                                    {
                                      String(
                                        secondsLeft % 60
                                      ).padStart(
                                        2,
                                        "0"
                                      )
                                    }
                                  </div>


                                  <div
                                    className="
                                      mt-1
                                      text-xs
                                      text-slate-500
                                    "
                                  >
                                    예약 확정까지 남은 시간
                                  </div>
                                </>
                              )

                            : (
                                <div
                                  className="
                                    mt-2
                                    text-sm
                                    text-emerald-700
                                  "
                                >
                                  HOLD 처리 완료
                                </div>
                              )
                        }

                      </div>
                    )

                  : (
                      <div
                        className="
                          mt-2
                          text-sm
                          text-slate-400
                        "
                      >
                        아직 HOLD가 없습니다.
                      </div>
                    )
              }

            </div>


            {/* CONFIRMED */}

            <div
              className="
                mt-3
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-bold
                  text-slate-400
                "
              >
                STEP 4
              </div>


              <div
                className="
                  mt-1
                  font-bold
                "
              >
                CONFIRMED
              </div>


              {
                appointment
                  ? (
                      <div
                        className="
                          mt-3
                          rounded-xl
                          bg-emerald-50
                          p-4
                        "
                      >

                        <div
                          className="
                            text-lg
                            font-bold
                            text-emerald-700
                          "
                        >
                          예약 완료 ✓
                        </div>


                        <div
                          className="
                            mt-3
                            space-y-1
                            text-sm
                            text-slate-600
                          "
                        >

                          <div>
                            Appointment #{appointment.id}
                          </div>

                          <div>
                            Hold #{appointment.hold_id}
                          </div>

                          <div>
                            Status: {appointment.status}
                          </div>

                        </div>

                      </div>
                    )

                  : (
                      <button
                        onClick={
                          confirmAppointment
                        }

                        disabled={
                          !hold
                          ||
                          hold.status !== "ACTIVE"
                          ||
                          secondsLeft <= 0
                          ||
                          loading
                        }

                        className="
                          mt-4
                          w-full
                          rounded-xl
                          bg-emerald-600
                          px-4
                          py-3
                          font-bold
                          text-white
                          hover:bg-emerald-500
                          disabled:cursor-not-allowed
                          disabled:opacity-40
                        "
                      >
                        예약 확정
                      </button>
                    )
              }

            </div>


            {/* ARCHITECTURE */}

            <div
              className="
                mt-6
                rounded-xl
                bg-slate-950
                p-4
                font-mono
                text-xs
                leading-6
                text-slate-300
              "
            >
              <div>Raw Hospital Data</div>
              <div>↓</div>
              <div>Normalization Layer</div>
              <div>↓</div>
              <div>Canonical ProviderOffer</div>
              <div>↓</div>
              <div>Patient Intent</div>
              <div>↓</div>
              <div>Constraint Match</div>
              <div>↓</div>
              <div>SHOWN → SELECTED → HELD → CONFIRMED</div>
            </div>

          </aside>

        </div>


        <div
          className="
            mt-6
            text-xs
            text-slate-400
          "
        >
          Synthetic prototype only. 병원명·의사명·가격은
          가상 데이터이며 constraint_match_score는
          의료적 품질이나 치료 추천 점수가 아닙니다.
        </div>

      </div>

    </main>
  );
}