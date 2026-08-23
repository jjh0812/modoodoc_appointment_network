"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";


const API_BASE =
  "http://127.0.0.1:8001";


type Candidate = {
  candidate_match_id: number;
  provider_id: number;
  provider_name: string;
  hospital_id: number;
  hospital_name: string;
  district: string;
  offer_id: number;
  procedure_code: string;
  procedure_name: string;
  price_min: number;
  price_max: number;
  earliest_slot_id: number;
  earliest_slot_time: string;
  constraint_match_score: number;
  budget_status: string;
  data_confidence: number;
  reasons: string[];
};


type CareOptionsResponse = {
  intent_id: number;
  candidates: Candidate[];
};


type Hold = {
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


type DecisionFeedbackResponse = {
  id: number;
  intent_id: number;
  candidate_match_id: number | null;
  feedback_type: string;
  reason_codes: string[];
  free_text: string | null;
  source: string;
  idempotency_key: string;
};


type SelectionReason =
  | "PRICE"
  | "AVAILABILITY"
  | "LOCATION"
  | "DATA_CONFIDENCE"
  | "OTHER";


type NoSelectionReason =
  | "BUDGET_TOO_HIGH"
  | "TIME_NOT_MATCH"
  | "LOCATION_NOT_MATCH"
  | "INSUFFICIENT_INFORMATION"
  | "OTHER";


const SELECTION_REASON_OPTIONS: {
  code: SelectionReason;
  label: string;
}[] = [
  {
    code: "PRICE",
    label: "가격",
  },
  {
    code: "AVAILABILITY",
    label: "예약 시간",
  },
  {
    code: "LOCATION",
    label: "위치",
  },
  {
    code: "DATA_CONFIDENCE",
    label: "정보 신뢰도",
  },
  {
    code: "OTHER",
    label: "기타",
  },
];


const NO_SELECTION_REASON_OPTIONS: {
  code: NoSelectionReason;
  label: string;
}[] = [
  {
    code: "BUDGET_TOO_HIGH",
    label: "예산 초과",
  },
  {
    code: "TIME_NOT_MATCH",
    label: "시간이 안 맞음",
  },
  {
    code: "LOCATION_NOT_MATCH",
    label: "위치가 안 맞음",
  },
  {
    code: "INSUFFICIENT_INFORMATION",
    label: "정보가 부족함",
  },
  {
    code: "OTHER",
    label: "기타",
  },
];


function formatPriceRange(
  min: number,
  max: number,
) {
  return (
    `${Math.round(min / 10000)}만원`
    +
    " ~ "
    +
    `${Math.round(max / 10000)}만원`
  );
}


function formatSlotTime(
  value: string,
) {
  const date =
    new Date(value);

  return date.toLocaleString(
    "ko-KR",
    {
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}


function budgetStatusLabel(
  status: string,
) {
  if (
    status
    === "WITHIN_BUDGET"
  ) {
    return "예산 범위 내";
  }

  if (
    status
    === "PARTIAL_MATCH"
  ) {
    return "예산 부분 일치";
  }

  return status;
}


async function readError(
  response: Response,
) {
  try {
    const data =
      await response.json();

    return (
      data.detail
      ??
      JSON.stringify(data)
    );
  } catch {
    return (
      `HTTP ${response.status}`
    );
  }
}


export default function Home() {

  // =====================================================
  // Patient Intent
  // =====================================================

  const [
    rawQuery,
    setRawQuery,
  ] = useState(
    "8월 22일 오후 강남에서 200만원 정도로 "
    +
    "스마일 시력교정 검진 가능한 곳 찾아줘"
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
    "2000000"
  );


  // =====================================================
  // Search / Transaction
  // =====================================================

  const [
    intentId,
    setIntentId,
  ] = useState<number | null>(
    null
  );


  const [
    candidates,
    setCandidates,
  ] = useState<Candidate[]>(
    []
  );


  const [
    selectedCandidate,
    setSelectedCandidate,
  ] = useState<Candidate | null>(
    null
  );


  const [
    hold,
    setHold,
  ] = useState<Hold | null>(
    null
  );


  const [
    appointment,
    setAppointment,
  ] = useState<Appointment | null>(
    null
  );


  const [
    secondsLeft,
    setSecondsLeft,
  ] = useState(
    0
  );


  const [
    loading,
    setLoading,
  ] = useState(
    false
  );


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  // =====================================================
  // Decision Feedback
  // =====================================================

  const [
    selectionReasons,
    setSelectionReasons,
  ] = useState<SelectionReason[]>(
    []
  );


  const [
    selectionFreeText,
    setSelectionFreeText,
  ] = useState(
    ""
  );


  const [
    selectionFeedback,
    setSelectionFeedback,
  ] =
    useState<DecisionFeedbackResponse | null>(
      null
    );


  const [
    noSelectionReasons,
    setNoSelectionReasons,
  ] =
    useState<NoSelectionReason[]>(
      []
    );


  const [
    noSelectionFreeText,
    setNoSelectionFreeText,
  ] = useState(
    ""
  );


  const [
    noSelectionFeedback,
    setNoSelectionFeedback,
  ] =
    useState<DecisionFeedbackResponse | null>(
      null
    );


  const [
    showNoSelectionFeedback,
    setShowNoSelectionFeedback,
  ] = useState(
    false
  );


  const [
    feedbackLoading,
    setFeedbackLoading,
  ] = useState(
    false
  );


  const [
    feedbackError,
    setFeedbackError,
  ] = useState<string | null>(
    null
  );


  // =====================================================
  // Stable idempotency keys
  // =====================================================

  const confirmKeyRef =
    useRef<string | null>(
      null
    );


  const selectionFeedbackKeyRef =
    useRef<string | null>(
      null
    );


  const noSelectionFeedbackKeyRef =
    useRef<string | null>(
      null
    );


  // =====================================================
  // HOLD countdown
  // =====================================================

  useEffect(() => {

    if (
      !hold
      ||
      hold.status
      !== "ACTIVE"
    ) {
      setSecondsLeft(0);
      return;
    }


    function calculate() {

      const expiresAt =
        new Date(
          hold!.expires_at
        ).getTime();


      const now =
        Date.now();


      const seconds =
        Math.max(
          0,
          Math.floor(
            (
              expiresAt
              - now
            )
            / 1000
          )
        );


      setSecondsLeft(
        seconds
      );
    }


    calculate();


    const timer =
      window.setInterval(
        calculate,
        1000
      );


    return () => {
      window.clearInterval(
        timer
      );
    };

  }, [hold]);


  // =====================================================
  // Search
  // =====================================================

  async function searchCareOptions() {

    setLoading(true);
    setError(null);
    setFeedbackError(null);

    setIntentId(null);
    setCandidates([]);
    setSelectedCandidate(null);
    setHold(null);
    setAppointment(null);

    setSelectionReasons([]);
    setSelectionFreeText("");
    setSelectionFeedback(null);

    setNoSelectionReasons([]);
    setNoSelectionFreeText("");
    setNoSelectionFeedback(null);
    setShowNoSelectionFeedback(false);

    confirmKeyRef.current = null;
    selectionFeedbackKeyRef.current = null;
    noSelectionFeedbackKeyRef.current = null;


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

                district,

                preferred_date:
                  preferredDate,

                time_window:
                  timeWindow,

                budget_max:
                  budgetMax
                    ? Number(
                        budgetMax
                      )
                    : null,

                source:
                  "AI_SIMULATOR",

                raw_query:
                  rawQuery,

                limit:
                  3,
              }
            ),
          }
        );


      if (!response.ok) {

        throw new Error(
          await readError(
            response
          )
        );
      }


      const data:
        CareOptionsResponse =
          await response.json();


      setIntentId(
        data.intent_id
      );


      setCandidates(
        data.candidates
      );


      noSelectionFeedbackKeyRef.current =
        (
          "ui-no-selection-"
          +
          crypto.randomUUID()
        );

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "검색 중 오류가 발생했습니다."
      );

    } finally {

      setLoading(false);
    }
  }


  // =====================================================
  // Candidate Select → HOLD
  // =====================================================

  async function selectCandidate(
    candidate: Candidate,
  ) {

    setLoading(true);
    setError(null);
    setFeedbackError(null);


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

        throw new Error(
          await readError(
            response
          )
        );
      }


      const data: Hold =
        await response.json();


      setSelectedCandidate(
        candidate
      );


      setHold(
        data
      );


      setAppointment(
        null
      );


      setSelectionReasons(
        []
      );


      setSelectionFreeText(
        ""
      );


      setSelectionFeedback(
        null
      );


      setShowNoSelectionFeedback(
        false
      );


      confirmKeyRef.current =
        null;


      selectionFeedbackKeyRef.current =
        (
          "ui-selection-"
          +
          crypto.randomUUID()
        );

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "후보 선택 중 오류가 발생했습니다."
      );

    } finally {

      setLoading(false);
    }
  }


  // =====================================================
  // HOLD → CONFIRM
  // =====================================================

  async function confirmAppointment() {

    if (!hold) {
      return;
    }


    setLoading(true);
    setError(null);


    try {

      if (
        !confirmKeyRef.current
      ) {

        confirmKeyRef.current =
          (
            "ui-confirm-"
            +
            crypto.randomUUID()
          );
      }


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
                  confirmKeyRef.current,
              }
            ),
          }
        );


      if (!response.ok) {

        throw new Error(
          await readError(
            response
          )
        );
      }


      const data:
        Appointment =
          await response.json();


      setAppointment(
        data
      );


      setHold(
        previous =>
          previous
            ? {
                ...previous,
                status:
                  "CONFIRMED",
              }
            : previous
      );

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "예약 확정 중 오류가 발생했습니다."
      );

    } finally {

      setLoading(false);
    }
  }


  // =====================================================
  // Selection Feedback reason toggle
  // =====================================================

  function toggleSelectionReason(
    reason: SelectionReason,
  ) {

    setSelectionReasons(
      previous =>
        previous.includes(
          reason
        )
          ? previous.filter(
              item =>
                item !== reason
            )
          : [
              ...previous,
              reason,
            ]
    );
  }


  // =====================================================
  // No-selection Feedback reason toggle
  // =====================================================

  function toggleNoSelectionReason(
    reason:
      NoSelectionReason,
  ) {

    setNoSelectionReasons(
      previous =>
        previous.includes(
          reason
        )
          ? previous.filter(
              item =>
                item !== reason
            )
          : [
              ...previous,
              reason,
            ]
    );
  }


  // =====================================================
  // Selection Feedback POST
  // =====================================================

  async function submitSelectionFeedback() {

    if (
      intentId === null
      ||
      selectedCandidate === null
      ||
      selectionReasons.length === 0
    ) {
      return;
    }


    setFeedbackLoading(true);
    setFeedbackError(null);


    try {

      if (
        !selectionFeedbackKeyRef.current
      ) {

        selectionFeedbackKeyRef.current =
          (
            "ui-selection-"
            +
            crypto.randomUUID()
          );
      }


      const response =
        await fetch(
          (
            `${API_BASE}`
            +
            "/decision-feedback/selection"
          ),
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                intent_id:
                  intentId,

                candidate_match_id:
                  selectedCandidate
                    .candidate_match_id,

                reason_codes:
                  selectionReasons,

                free_text:
                  selectionFreeText
                    .trim()
                  ||
                  null,

                source:
                  "AI_SIMULATOR",

                idempotency_key:
                  selectionFeedbackKeyRef
                    .current,
              }
            ),
          }
        );


      if (!response.ok) {

        throw new Error(
          await readError(
            response
          )
        );
      }


      const data:
        DecisionFeedbackResponse =
          await response.json();


      setSelectionFeedback(
        data
      );

    } catch (err) {

      setFeedbackError(
        err instanceof Error
          ? err.message
          : "선택 이유 저장 중 오류가 발생했습니다."
      );

    } finally {

      setFeedbackLoading(false);
    }
  }


  // =====================================================
  // No-selection Feedback POST
  // =====================================================

  async function submitNoSelectionFeedback() {

    if (
      intentId === null
      ||
      selectedCandidate !== null
      ||
      noSelectionReasons.length === 0
    ) {
      return;
    }


    setFeedbackLoading(true);
    setFeedbackError(null);


    try {

      if (
        !noSelectionFeedbackKeyRef.current
      ) {

        noSelectionFeedbackKeyRef.current =
          (
            "ui-no-selection-"
            +
            crypto.randomUUID()
          );
      }


      const response =
        await fetch(
          (
            `${API_BASE}`
            +
            "/decision-feedback/no-selection"
          ),
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                intent_id:
                  intentId,

                reason_codes:
                  noSelectionReasons,

                free_text:
                  noSelectionFreeText
                    .trim()
                  ||
                  null,

                source:
                  "AI_SIMULATOR",

                idempotency_key:
                  noSelectionFeedbackKeyRef
                    .current,
              }
            ),
          }
        );


      if (!response.ok) {

        throw new Error(
          await readError(
            response
          )
        );
      }


      const data:
        DecisionFeedbackResponse =
          await response.json();


      setNoSelectionFeedback(
        data
      );

    } catch (err) {

      setFeedbackError(
        err instanceof Error
          ? err.message
          : "비선택 이유 저장 중 오류가 발생했습니다."
      );

    } finally {

      setFeedbackLoading(false);
    }
  }


  // =====================================================
  // UI
  // =====================================================

  return (

    <main
      className="
        min-h-screen
        bg-slate-50
        text-slate-950
      "
    >

      <div
        className="
          mx-auto
          max-w-7xl
          px-6
          py-10
        "
      >

        {/* =================================================
            HEADER
        ================================================= */}

        <div
          className="
            mb-8
            flex
            flex-wrap
            items-start
            justify-between
            gap-4
          "
        >

          <div>

            <div
              className="
                text-xs
                font-bold
                uppercase
                tracking-[0.18em]
                text-slate-400
              "
            >
              MODOODOC EXECUTABLE DECISION NETWORK
            </div>


            <h1
              className="
                mt-2
                text-4xl
                font-black
                tracking-tight
              "
            >
              AI Care Decision Simulator
            </h1>


            <p
              className="
                mt-3
                max-w-3xl
                text-sm
                leading-6
                text-slate-500
              "
            >
              환자의 자연어 요청을 canonical healthcare data,
              실제 availability, transaction graph와 연결합니다.
            </p>

          </div>


          <a
            href="/analytics"
            className="
              rounded-xl
              border
              border-slate-200
              bg-white
              px-4
              py-3
              text-sm
              font-bold
              shadow-sm
              hover:bg-slate-50
            "
          >
            Decision Analytics →
          </a>

        </div>


        <div
          className="
            grid
            gap-6
            lg:grid-cols-[minmax(0,1fr)_360px]
          "
        >

          {/* =================================================
              LEFT
          ================================================= */}

          <section>

            {/* ==============================================
                PATIENT INTENT
            ============================================== */}

            <div
              className="
                rounded-2xl
                border
                border-slate-200
                bg-white
                p-6
                shadow-sm
              "
            >

              <div
                className="
                  text-xs
                  font-bold
                  uppercase
                  tracking-wide
                  text-slate-400
                "
              >
                Patient Intent
              </div>


              <h2
                className="
                  mt-1
                  text-xl
                  font-bold
                "
              >
                원하는 진료 조건
              </h2>


              <div
                className="
                  mt-5
                  space-y-4
                "
              >

                <div>

                  <label
                    className="
                      text-sm
                      font-bold
                    "
                  >
                    자연어 요청
                  </label>


                  <textarea
                    value={rawQuery}

                    onChange={
                      event =>
                        setRawQuery(
                          event.target.value
                        )
                    }

                    className="
                      mt-2
                      min-h-24
                      w-full
                      rounded-xl
                      border
                      border-slate-200
                      p-3
                      outline-none
                      focus:border-blue-500
                    "
                  />

                </div>


                <div
                  className="
                    grid
                    gap-3
                    sm:grid-cols-2
                  "
                >

                  <IntentInput
                    label="지역"
                    value={district}
                    onChange={setDistrict}
                  />


                  <IntentInput
                    label="날짜"
                    type="date"
                    value={preferredDate}
                    onChange={setPreferredDate}
                  />


                  <div>

                    <label
                      className="
                        text-sm
                        font-bold
                      "
                    >
                      시간대
                    </label>


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
                        border-slate-200
                        bg-white
                        p-3
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
                        시간 무관
                      </option>
                    </select>

                  </div>


                  <IntentInput
                    label="최대 예산"
                    type="number"
                    value={budgetMax}
                    onChange={setBudgetMax}
                  />

                </div>


                <button
                  onClick={
                    searchCareOptions
                  }

                  disabled={loading}

                  className="
                    w-full
                    rounded-xl
                    bg-slate-950
                    px-4
                    py-3
                    font-bold
                    text-white
                    hover:bg-slate-800
                    disabled:opacity-40
                  "
                >
                  {
                    loading
                      ? "처리 중..."
                      : "실행 가능한 후보 찾기"
                  }
                </button>

              </div>

            </div>


            {
              error
              &&
              (
                <div
                  className="
                    mt-4
                    rounded-xl
                    border
                    border-red-200
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


                                          <div
                                            className="
                                              mt-4
                                              grid
                                              gap-3
                                              sm:grid-cols-3
                                            "
                                          >

                                            <InfoBox
                                              label="예상 가격"
                                              value={
                                                formatPriceRange(
                                                  candidate.price_min,
                                                  candidate.price_max
                                                )
                                              }
                                            />


                                            <InfoBox
                                              label="가장 빠른 슬롯"
                                              value={
                                                formatSlotTime(
                                                  candidate
                                                    .earliest_slot_time
                                                )
                                              }
                                            />


                                            <InfoBox
                                              label="데이터 Confidence"
                                              value={
                                                candidate
                                                  .data_confidence
                                                  .toFixed(2)
                                              }
                                            />

                                          </div>


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


                  {/* =============================================
                      NO-SELECTION FEEDBACK
                  ============================================= */}

                  {
                    candidates.length > 0
                    &&
                    selectedCandidate === null
                    &&
                    (
                      <div
                        className="
                          mt-5
                          rounded-2xl
                          border
                          border-dashed
                          border-slate-300
                          bg-white
                          p-5
                        "
                      >

                        {
                          noSelectionFeedback
                            ? (
                                <FeedbackSaved
                                  id={
                                    noSelectionFeedback.id
                                  }
                                  text="비선택 이유가 저장되었습니다."
                                />
                              )

                            : (
                                <>

                                  <button
                                    onClick={
                                      () =>
                                        setShowNoSelectionFeedback(
                                          previous =>
                                            !previous
                                        )
                                    }

                                    className="
                                      text-sm
                                      font-bold
                                      text-slate-700
                                      underline
                                      underline-offset-4
                                    "
                                  >
                                    마음에 드는 후보가 없나요?
                                  </button>


                                  {
                                    showNoSelectionFeedback
                                    &&
                                    (
                                      <div
                                        className="
                                          mt-4
                                        "
                                      >

                                        <h3
                                          className="
                                            font-bold
                                          "
                                        >
                                          왜 아무 후보도 선택하지 않았나요?
                                        </h3>


                                        <p
                                          className="
                                            mt-1
                                            text-xs
                                            text-slate-500
                                          "
                                        >
                                          실제 사용자 응답과
                                          시스템이 관측한 Loss Signal을
                                          분리해서 저장합니다.
                                        </p>


                                        <div
                                          className="
                                            mt-4
                                            flex
                                            flex-wrap
                                            gap-2
                                          "
                                        >
                                          {
                                            NO_SELECTION_REASON_OPTIONS
                                              .map(
                                                option => (

                                                  <ReasonChip
                                                    key={
                                                      option.code
                                                    }

                                                    selected={
                                                      noSelectionReasons
                                                        .includes(
                                                          option.code
                                                        )
                                                    }

                                                    label={
                                                      option.label
                                                    }

                                                    onClick={
                                                      () =>
                                                        toggleNoSelectionReason(
                                                          option.code
                                                        )
                                                    }
                                                  />

                                                )
                                              )
                                          }
                                        </div>


                                        <textarea
                                          value={
                                            noSelectionFreeText
                                          }

                                          onChange={
                                            event =>
                                              setNoSelectionFreeText(
                                                event.target.value
                                              )
                                          }

                                          placeholder="추가로 알려주실 내용이 있다면 적어주세요."

                                          className="
                                            mt-4
                                            min-h-20
                                            w-full
                                            rounded-xl
                                            border
                                            border-slate-200
                                            p-3
                                            text-sm
                                          "
                                        />


                                        <button
                                          onClick={
                                            submitNoSelectionFeedback
                                          }

                                          disabled={
                                            feedbackLoading
                                            ||
                                            noSelectionReasons
                                              .length
                                            === 0
                                          }

                                          className="
                                            mt-3
                                            w-full
                                            rounded-xl
                                            bg-slate-800
                                            px-4
                                            py-3
                                            text-sm
                                            font-bold
                                            text-white
                                            disabled:opacity-40
                                          "
                                        >
                                          비선택 이유 저장
                                        </button>

                                      </div>
                                    )
                                  }

                                </>
                              )
                        }

                      </div>
                    )
                  }

                </div>
              )
            }


            {/* =================================================
                SELECTION FEEDBACK
            ================================================= */}

            {
              selectedCandidate
              &&
              intentId !== null
              &&
              (
                <div
                  className="
                    mt-6
                    rounded-2xl
                    border
                    border-blue-200
                    bg-blue-50
                    p-6
                  "
                >

                  <div
                    className="
                      text-xs
                      font-bold
                      uppercase
                      tracking-wide
                      text-blue-500
                    "
                  >
                    DECISION FEEDBACK
                  </div>


                  {
                    selectionFeedback
                      ? (
                          <FeedbackSaved
                            id={
                              selectionFeedback.id
                            }
                            text="선택 이유가 저장되었습니다."
                          />
                        )

                      : (
                          <>

                            <h2
                              className="
                                mt-2
                                text-lg
                                font-bold
                              "
                            >
                              왜 이 후보를 선택했나요?
                            </h2>


                            <p
                              className="
                                mt-1
                                text-sm
                                text-slate-600
                              "
                            >
                              {
                                selectedCandidate
                                  .hospital_name
                              }
                              을 선택한 이유를 알려주세요.
                              여러 개 선택할 수 있습니다.
                            </p>


                            <div
                              className="
                                mt-4
                                flex
                                flex-wrap
                                gap-2
                              "
                            >
                              {
                                SELECTION_REASON_OPTIONS
                                  .map(
                                    option => (

                                      <ReasonChip
                                        key={
                                          option.code
                                        }

                                        selected={
                                          selectionReasons
                                            .includes(
                                              option.code
                                            )
                                        }

                                        label={
                                          option.label
                                        }

                                        onClick={
                                          () =>
                                            toggleSelectionReason(
                                              option.code
                                            )
                                        }
                                      />

                                    )
                                  )
                              }
                            </div>


                            <textarea
                              value={
                                selectionFreeText
                              }

                              onChange={
                                event =>
                                  setSelectionFreeText(
                                    event.target.value
                                  )
                              }

                              placeholder="예: 예산 안이고 원하는 시간이 있어서 선택했어요."

                              className="
                                mt-4
                                min-h-20
                                w-full
                                rounded-xl
                                border
                                border-blue-200
                                bg-white
                                p-3
                                text-sm
                              "
                            />


                            <button
                              onClick={
                                submitSelectionFeedback
                              }

                              disabled={
                                feedbackLoading
                                ||
                                selectionReasons
                                  .length
                                === 0
                              }

                              className="
                                mt-3
                                w-full
                                rounded-xl
                                bg-blue-600
                                px-4
                                py-3
                                font-bold
                                text-white
                                hover:bg-blue-500
                                disabled:opacity-40
                              "
                            >
                              {
                                feedbackLoading
                                  ? "저장 중..."
                                  : "선택 이유 저장"
                              }
                            </button>

                          </>
                        )
                  }

                </div>
              )
            }


            {
              feedbackError
              &&
              (
                <div
                  className="
                    mt-4
                    rounded-xl
                    border
                    border-red-200
                    bg-red-50
                    p-4
                    text-sm
                    text-red-700
                  "
                >
                  {feedbackError}
                </div>
              )
            }

          </section>


          {/* =================================================
              RIGHT — TRANSACTION GRAPH
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


            <TransactionStep
              step="STEP 1"
              title="SHOWN"
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
            </TransactionStep>


            <TransactionStep
              step="STEP 2"
              title="SELECTED"
            >
              {
                selectedCandidate
                  ? (
                      <>
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
                      </>
                    )

                  : (
                      "아직 선택된 후보가 없습니다."
                    )
              }
            </TransactionStep>


            <div
              className="
                mt-3
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <StepHeader
                step="STEP 3"
                title="HELD"
              />


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
                          hold.status
                          === "ACTIVE"
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
                                        secondsLeft
                                        / 60
                                      )
                                    }
                                    :
                                    {
                                      String(
                                        secondsLeft
                                        % 60
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


            <div
              className="
                mt-3
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <StepHeader
                step="STEP 4"
                title="CONFIRMED"
              />


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
                          hold.status
                          !== "ACTIVE"
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


            {/* =================================================
                FEEDBACK LAYER
            ================================================= */}

            <div
              className="
                mt-3
                rounded-xl
                border
                border-purple-200
                bg-purple-50
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-bold
                  text-purple-500
                "
              >
                STEP 5
              </div>


              <div
                className="
                  mt-1
                  font-bold
                "
              >
                DECISION FEEDBACK
              </div>


              <div
                className="
                  mt-2
                  text-sm
                  text-slate-600
                "
              >
                {
                  selectionFeedback
                    ? (
                        `Selection Feedback #${selectionFeedback.id} 저장 완료`
                      )

                    : noSelectionFeedback
                      ? (
                          `No-Selection Feedback #${noSelectionFeedback.id} 저장 완료`
                        )

                      : (
                          "사용자가 직접 밝힌 선택·비선택 이유를 기록합니다."
                        )
                }
              </div>

            </div>


            {/* =================================================
                ARCHITECTURE
            ================================================= */}

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
              <div>
                SHOWN → SELECTED → HELD → CONFIRMED
              </div>
              <div>↓</div>
              <div>
                Decision Feedback
              </div>
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
          Decision Feedback은 사용자가 직접 밝힌 이유이고,
          Decision Loss Signal은 시스템이 관측한 차이입니다.
        </div>

      </div>

    </main>
  );
}


// =========================================================
// Small UI Components
// =========================================================

function IntentInput({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (
    value: string
  ) => void;
  type?: string;
}) {

  return (
    <div>

      <label
        className="
          text-sm
          font-bold
        "
      >
        {label}
      </label>


      <input
        type={type}
        value={value}

        onChange={
          event =>
            onChange(
              event.target.value
            )
        }

        className="
          mt-2
          w-full
          rounded-xl
          border
          border-slate-200
          p-3
        "
      />

    </div>
  );
}


function InfoBox({
  label,
  value,
}: {
  label: string;
  value: string;
}) {

  return (
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
        {label}
      </div>


      <div
        className="
          mt-1
          font-bold
        "
      >
        {value}
      </div>

    </div>
  );
}


function ReasonChip({
  selected,
  label,
  onClick,
}: {
  selected: boolean;
  label: string;
  onClick: () => void;
}) {

  return (
    <button
      type="button"
      onClick={onClick}

      className={`
        rounded-full
        border
        px-4
        py-2
        text-sm
        font-bold
        transition

        ${
          selected
            ? "border-blue-600 bg-blue-600 text-white"
            : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
        }
      `}
    >
      {label}
    </button>
  );
}


function FeedbackSaved({
  id,
  text,
}: {
  id: number;
  text: string;
}) {

  return (
    <div
      className="
        rounded-xl
        border
        border-emerald-200
        bg-emerald-50
        p-4
      "
    >

      <div
        className="
          font-bold
          text-emerald-700
        "
      >
        {text}
      </div>


      <div
        className="
          mt-1
          text-xs
          text-emerald-600
        "
      >
        DecisionFeedback #{id}
      </div>

    </div>
  );
}


function StepHeader({
  step,
  title,
}: {
  step: string;
  title: string;
}) {

  return (
    <>
      <div
        className="
          text-xs
          font-bold
          text-slate-400
        "
      >
        {step}
      </div>

      <div
        className="
          mt-1
          font-bold
        "
      >
        {title}
      </div>
    </>
  );
}


function TransactionStep({
  step,
  title,
  children,
}: {
  step: string;
  title: string;
  children:
    React.ReactNode;
}) {

  return (
    <div
      className="
        mt-3
        rounded-xl
        border
        border-slate-200
        p-4
      "
    >

      <StepHeader
        step={step}
        title={title}
      />


      <div
        className="
          mt-2
          text-sm
          text-slate-600
        "
      >
        {children}
      </div>

    </div>
  );
}