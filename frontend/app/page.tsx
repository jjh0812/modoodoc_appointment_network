"use client";

import {
  useEffect,
  useState,
} from "react";


const API_BASE =
  "http://127.0.0.1:8001";


type AppointmentSlot = {
  id: number;
  provider_id: number;
  start_time: string;
  status: string;
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
// HOLD expires_at은 UTC 기준으로 저장했기 때문에
// 브라우저에서 UTC로 읽도록 처리
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
// Main Page
// =========================================================

export default function Home() {

  // -------------------------------------------------------
  // 사용자가 AI에게 입력한 문장
  // -------------------------------------------------------

  const [
    query,
    setQuery,
  ] = useState(
    "8월 22일 오후에 시력교정 검사 예약 가능한 시간 찾아줘"
  );


  // -------------------------------------------------------
  // API에서 가져온 AVAILABLE 슬롯
  // -------------------------------------------------------

  const [
    slots,
    setSlots,
  ] = useState<AppointmentSlot[]>([]);


  // -------------------------------------------------------
  // 현재 HOLD
  // -------------------------------------------------------

  const [
    hold,
    setHold,
  ] = useState<SlotHold | null>(
    null
  );


  // -------------------------------------------------------
  // 확정된 Appointment
  // -------------------------------------------------------

  const [
    appointment,
    setAppointment,
  ] = useState<Appointment | null>(
    null
  );


  // -------------------------------------------------------
  // 같은 CONFIRM retry에 계속 사용할 key
  // -------------------------------------------------------

  const [
    idempotencyKey,
    setIdempotencyKey,
  ] = useState<string | null>(
    null
  );


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  // -------------------------------------------------------
  // HOLD 남은 시간
  // -------------------------------------------------------

  const [
    secondsLeft,
    setSecondsLeft,
  ] = useState(0);


  // =======================================================
  // HOLD countdown
  // =======================================================

  useEffect(
    () => {

      // HOLD가 없거나
      // 이미 CONFIRMED 상태라면
      // countdown을 돌릴 필요가 없음

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
  // 1. Availability 조회
  // =======================================================

  async function searchAvailability() {

    setLoading(true);

    setError("");


    try {

      const response =
        await fetch(
          `${API_BASE}/providers/1/availability`
        );


      if (!response.ok) {

        throw new Error(
          "예약 가능시간 조회에 실패했습니다."
        );
      }


      const data:
        AppointmentSlot[] =
        await response.json();


      setSlots(
        data
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
  // 2. 슬롯 HOLD
  // =======================================================

  async function holdSlot(
    slotId: number
  ) {

    setLoading(true);

    setError("");


    try {

      const response =
        await fetch(
          `${API_BASE}/slots/${slotId}/hold`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                source: "ChatGPT",
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
          "HOLD에 실패했습니다."
        );
      }


      const data:
        SlotHold =
        await response.json();


      setHold(
        data
      );


      // 이전 예약 결과가 있었다면 초기화
      setAppointment(
        null
      );


      // -----------------------------------------------
      // 이 HOLD의 CONFIRM retry들은
      // 모두 같은 idempotency key를 사용
      // -----------------------------------------------

      setIdempotencyKey(
        crypto.randomUUID()
      );


      // -----------------------------------------------
      // HOLD된 슬롯은 AVAILABLE 목록에서 제거
      // -----------------------------------------------

      setSlots(
        currentSlots =>
          currentSlots.filter(
            slot =>
              slot.id !== slotId
          )
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
  // 3. 예약 CONFIRM
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
          `${API_BASE}/holds/${hold.id}/confirm`,
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


      // -----------------------------------------------
      // Appointment 화면 상태 업데이트
      // -----------------------------------------------

      setAppointment(
        data
      );


      // -----------------------------------------------
      // 중요:
      //
      // 백엔드에서는 CONFIRM 성공 시
      //
      // SlotHold
      // ACTIVE → CONFIRMED
      //
      // 로 바뀌므로
      // 프론트의 hold 상태도 같이 갱신한다.
      // -----------------------------------------------

      setHold(
        currentHold =>
          currentHold
            ? {
                ...currentHold,
                status: "CONFIRMED",
              }
            : null
      );


      // -----------------------------------------------
      // 예약이 확정됐으므로 countdown 종료
      // -----------------------------------------------

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
  // 화면
  // =======================================================

  return (

    <main
      className="
        min-h-screen
        bg-slate-50
        px-6
        py-12
        text-slate-900
      "
    >

      <div
        className="
          mx-auto
          max-w-5xl
        "
      >

        {/* =================================================
            Header
        ================================================= */}

        <div
          className="
            mb-10
          "
        >

          <div
            className="
              mb-3
              text-sm
              font-semibold
              tracking-wide
              text-blue-600
            "
          >
            MODOODOC APPOINTMENT NETWORK
          </div>


          <h1
            className="
              text-4xl
              font-bold
              tracking-tight
            "
          >
            AI Booking Simulator
          </h1>


          <p
            className="
              mt-4
              max-w-2xl
              text-slate-600
            "
          >
            외부 AI가 병원의 실제 예약 가능시간을
            조회하고, 슬롯을 HOLD한 뒤,
            안전하게 예약을 확정하는 프로토타입입니다.
          </p>

        </div>


        <div
          className="
            grid
            gap-6
            lg:grid-cols-2
          "
        >

          {/* =================================================
              왼쪽: AI Simulator
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

            <div
              className="
                mb-5
                text-lg
                font-semibold
              "
            >
              AI Assistant
            </div>


            {/* USER MESSAGE */}

            <div
              className="
                mb-5
                ml-auto
                max-w-[90%]
                rounded-2xl
                bg-blue-600
                p-4
                text-white
              "
            >
              {query}
            </div>


            {/* INPUT */}

            <textarea
              value={query}

              onChange={
                event =>
                  setQuery(
                    event.target.value
                  )
              }

              className="
                min-h-24
                w-full
                resize-none
                rounded-xl
                border
                border-slate-300
                p-4
                outline-none
                transition
                focus:border-blue-500
              "
            />


            <button
              onClick={
                searchAvailability
              }

              disabled={loading}

              className="
                mt-3
                w-full
                rounded-xl
                bg-slate-900
                px-5
                py-3
                font-semibold
                text-white
                transition
                hover:bg-slate-700
                disabled:opacity-50
              "
            >
              {
                loading
                  ? "처리 중..."
                  : "예약 가능한 시간 찾기"
              }
            </button>


            {/* AVAILABLE SLOTS */}

            {
              slots.length > 0
              &&
              (
                <div
                  className="
                    mt-6
                    rounded-2xl
                    bg-slate-100
                    p-5
                  "
                >

                  <div
                    className="
                      mb-1
                      font-semibold
                    "
                  >
                    김OO 원장
                  </div>


                  <div
                    className="
                      mb-4
                      text-sm
                      text-slate-500
                    "
                  >
                    안과 · 시력교정
                  </div>


                  <div
                    className="
                      space-y-3
                    "
                  >

                    {
                      slots.map(
                        slot => (

                          <button
                            key={slot.id}

                            onClick={
                              () =>
                                holdSlot(
                                  slot.id
                                )
                            }

                            disabled={
                              loading
                              ||
                              (
                                hold !== null
                                &&
                                hold.status === "ACTIVE"
                              )
                            }

                            className="
                              flex
                              w-full
                              items-center
                              justify-between
                              rounded-xl
                              border
                              border-slate-200
                              bg-white
                              p-4
                              text-left
                              transition
                              hover:border-blue-400
                              hover:bg-blue-50
                              disabled:cursor-not-allowed
                              disabled:opacity-50
                            "
                          >

                            <span
                              className="
                                font-medium
                              "
                            >
                              {
                                formatSlotTime(
                                  slot.start_time
                                )
                              }
                            </span>


                            <span
                              className="
                                rounded-full
                                bg-emerald-100
                                px-3
                                py-1
                                text-xs
                                font-semibold
                                text-emerald-700
                              "
                            >
                              AVAILABLE
                            </span>

                          </button>

                        )
                      )
                    }

                  </div>

                </div>
              )
            }


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

          </section>


          {/* =================================================
              오른쪽: Transaction 상태
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

            <div
              className="
                mb-6
                text-lg
                font-semibold
              "
            >
              Transaction
            </div>


            {/* AVAILABLE */}

            <div
              className="
                mb-4
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-semibold
                  text-slate-400
                "
              >
                STEP 1
              </div>


              <div
                className="
                  mt-1
                  font-semibold
                "
              >
                Availability
              </div>


              <div
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                병원의 실제 AVAILABLE 슬롯 조회
              </div>

            </div>


            {/* HOLD */}

            <div
              className="
                mb-4
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-semibold
                  text-slate-400
                "
              >
                STEP 2
              </div>


              <div
                className="
                  mt-1
                  font-semibold
                "
              >
                HOLD
              </div>


              {
                hold
                  ? (
                      <div
                        className="
                          mt-3
                        "
                      >

                        {/* -----------------------------------
                            HOLD 상태를 하드코딩하지 않고
                            실제 React 상태를 표시
                        ----------------------------------- */}

                        <div
                          className="
                            text-sm
                            font-semibold
                            text-emerald-700
                          "
                        >
                          Hold #{hold.id} {hold.status}
                        </div>


                        {/* -----------------------------------
                            ACTIVE인 동안에만 countdown 표시
                        ----------------------------------- */}

                        {
                          hold.status === "ACTIVE"
                            ? (
                                <>
                                  <div
                                    className="
                                      mt-2
                                      text-3xl
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
                                    font-semibold
                                    text-emerald-700
                                  "
                                >
                                  예약 확정 완료
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
                        아직 HOLD된 슬롯이 없습니다.
                      </div>
                    )
              }

            </div>


            {/* CONFIRM */}

            <div
              className="
                rounded-xl
                border
                border-slate-200
                p-4
              "
            >

              <div
                className="
                  text-xs
                  font-semibold
                  text-slate-400
                "
              >
                STEP 3
              </div>


              <div
                className="
                  mt-1
                  font-semibold
                "
              >
                Confirm
              </div>


              {
                appointment
                  ? (
                      <div
                        className="
                          mt-4
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
                            Source: {appointment.source}
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
                          loading
                          ||
                          secondsLeft <= 0
                        }

                        className="
                          mt-4
                          w-full
                          rounded-xl
                          bg-blue-600
                          px-5
                          py-3
                          font-semibold
                          text-white
                          transition
                          hover:bg-blue-500
                          disabled:cursor-not-allowed
                          disabled:opacity-40
                        "
                      >
                        예약 확정
                      </button>
                    )
              }

            </div>


            {/* Architecture */}

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

              <div>
                AI / Browser
              </div>

              <div>
                ↓
              </div>

              <div>
                FastAPI :8001
              </div>

              <div>
                ↓
              </div>

              <div>
                PostgreSQL :5434
              </div>

              <div>
                ↓
              </div>

              <div>
                AVAILABLE → HELD → CONFIRMED
              </div>

            </div>

          </section>

        </div>


        <div
          className="
            mt-6
            text-xs
            text-slate-400
          "
        >
          Prototype note: 현재 자연어 문장은
          Provider #1의 availability API 호출로
          매핑하는 simulator이며,
          실제 LLM intent parsing은 아직 연결하지 않았습니다.
        </div>

      </div>

    </main>
  );
}