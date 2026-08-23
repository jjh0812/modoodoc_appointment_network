"use client";

import {
  useEffect,
  useState,
} from "react";

import HospitalDecisionTable
  from "./HospitalDecisionTable";


type FunnelData = {
  funnel: {
    searched: number;
    shown: number;
    selected: number;
    held: number;
    confirmed: number;
  };

  conversion_rates_pct: {
    search_to_shown: number;
    shown_to_selected: number;
    selected_to_held: number;
    held_to_confirmed: number;
    search_to_confirmed: number;
  };

  event_counts: {
    shown: number;
    selected: number;
    held: number;
    confirmed: number;
  };

  searches_by_source:
    Record<string, number>;
};


type ReasonSummary = {
  reason_code: string;
  count: number;
  feedback_share_pct: number;
};


type FeedbackSummary = {
  total_feedback: number;

  selection_feedback: {
    feedback_count: number;
    reasons: ReasonSummary[];
  };

  no_selection_feedback: {
    feedback_count: number;
    reasons: ReasonSummary[];
  };
};


const API_BASE =
  "http://127.0.0.1:8001";


const REASON_LABELS:
  Record<string, string> = {

    PRICE:
      "가격",

    AVAILABILITY:
      "예약 시간",

    LOCATION:
      "위치",

    DATA_CONFIDENCE:
      "정보 신뢰도",

    BUDGET_TOO_HIGH:
      "예산 초과",

    TIME_NOT_MATCH:
      "시간이 안 맞음",

    LOCATION_NOT_MATCH:
      "위치가 안 맞음",

    INSUFFICIENT_INFORMATION:
      "정보 부족",

    OTHER:
      "기타",
  };


export default function AnalyticsPage() {

  const [
    funnel,
    setFunnel,
  ] = useState<FunnelData | null>(
    null
  );


  const [
    feedback,
    setFeedback,
  ] = useState<FeedbackSummary | null>(
    null
  );


  const [
    loading,
    setLoading,
  ] = useState(
    true
  );


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  useEffect(() => {

    async function load() {

      try {

        setLoading(true);
        setError(null);


        const [
          funnelResponse,
          feedbackResponse,
        ] = await Promise.all([
          fetch(
            `${API_BASE}/analytics/decision-funnel`,
            {
              cache:
                "no-store",
            }
          ),

          fetch(
            `${API_BASE}/analytics/decision-feedback-summary`,
            {
              cache:
                "no-store",
            }
          ),
        ]);


        if (!funnelResponse.ok) {

          throw new Error(
            "전체 의사결정 데이터를 불러오지 못했습니다."
          );
        }


        if (!feedbackResponse.ok) {

          throw new Error(
            "사용자 이유 데이터를 불러오지 못했습니다."
          );
        }


        const funnelData:
          FunnelData =
            await funnelResponse.json();


        const feedbackData:
          FeedbackSummary =
            await feedbackResponse.json();


        setFunnel(
          funnelData
        );


        setFeedback(
          feedbackData
        );

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : "데이터를 불러오지 못했습니다."
        );

      } finally {

        setLoading(
          false
        );
      }
    }


    load();

  }, []);


  if (loading) {

    return (
      <main
        className="
          min-h-screen
          bg-slate-50
          p-10
        "
      >
        데이터를 불러오는 중...
      </main>
    );
  }


  if (
    error
    ||
    !funnel
    ||
    !feedback
  ) {

    return (
      <main
        className="
          min-h-screen
          bg-slate-50
          p-10
        "
      >
        <div
          className="
            mx-auto
            max-w-3xl
            rounded-2xl
            border
            bg-white
            p-6
          "
        >
          <h1
            className="
              text-xl
              font-bold
            "
          >
            Analytics 연결 실패
          </h1>

          <p
            className="
              mt-2
              text-slate-500
            "
          >
            {error}
          </p>
        </div>
      </main>
    );
  }


  const droppedAfterShown =
    Math.max(
      0,
      funnel.funnel.shown
      -
      funnel.funnel.selected
    );


  const dropRateAfterShown =
    funnel.funnel.shown > 0
      ? Math.round(
          (
            droppedAfterShown
            /
            funnel.funnel.shown
          )
          *
          1000
        )
        / 10

      : 0;


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

        {/* =============================================
            HEADER
        ============================================= */}

        <div>

          <div
            className="
              text-xs
              font-bold
              tracking-[0.16em]
              text-slate-400
            "
          >
            MODOODOC DECISION INTELLIGENCE
          </div>


          <h1
            className="
              mt-2
              text-4xl
              font-black
              tracking-tight
            "
          >
            환자 선택 현황
          </h1>


          <p
            className="
              mt-2
              text-slate-500
            "
          >
            어디에서 환자가 이탈하고,
            어떤 이유로 선택하는지 한눈에 봅니다.
          </p>

        </div>


        {/* =============================================
            FUNNEL — 가장 단순한 숫자
        ============================================= */}

        <section
          className="
            mt-8
            grid
            gap-3
            md:grid-cols-4
          "
        >

          <SimpleNumber
            label="검색"
            value={
              funnel.funnel.searched
            }
          />


          <SimpleNumber
            label="후보 제시"
            value={
              funnel.funnel.shown
            }
          />


          <SimpleNumber
            label="후보 선택"
            value={
              funnel.funnel.selected
            }
          />


          <SimpleNumber
            label="예약 완료"
            value={
              funnel.funnel.confirmed
            }
          />

        </section>


        {/* =============================================
            가장 큰 문제
        ============================================= */}

        <section
          className="
            mt-5
            rounded-2xl
            bg-slate-950
            p-7
            text-white
          "
        >

          <div
            className="
              text-xs
              font-bold
              text-slate-400
            "
          >
            가장 큰 이탈 구간
          </div>


          <div
            className="
              mt-3
              grid
              items-end
              gap-5
              md:grid-cols-[1fr_auto]
            "
          >

            <div>

              <h2
                className="
                  text-2xl
                  font-bold
                "
              >
                후보를 본 뒤 선택하지 않음
              </h2>


              <p
                className="
                  mt-2
                  text-slate-300
                "
              >
                후보를 받은{" "}
                <strong>
                  {funnel.funnel.shown}건
                </strong>
                중{" "}
                <strong>
                  {droppedAfterShown}건
                </strong>
                이 후보 선택으로 이어지지 않았습니다.
              </p>

            </div>


            <div
              className="
                text-right
              "
            >

              <div
                className="
                  text-5xl
                  font-black
                "
              >
                {dropRateAfterShown}%
              </div>


              <div
                className="
                  mt-1
                  text-xs
                  text-slate-400
                "
              >
                후보 노출 → 선택 이탈률
              </div>

            </div>

          </div>


          <div
            className="
              mt-6
              h-3
              overflow-hidden
              rounded-full
              bg-slate-700
            "
          >

            <div
              className="
                h-full
                bg-white
              "

              style={{
                width:
                  `${Math.min(
                    dropRateAfterShown,
                    100
                  )}%`,
              }}
            />

          </div>

        </section>


        {/* =============================================
            이유
        ============================================= */}

        <section
          className="
            mt-5
            grid
            gap-5
            lg:grid-cols-2
          "
        >

          {/* 선택 이유 */}

          <div
            className="
              rounded-2xl
              border
              border-slate-200
              bg-white
              p-6
            "
          >

            <div
              className="
                text-xs
                font-bold
                text-slate-400
              "
            >
              왜 선택했나?
            </div>


            <h2
              className="
                mt-1
                text-xl
                font-bold
              "
            >
              사용자가 직접 말한 선택 이유
            </h2>


            <div
              className="
                mt-1
                text-xs
                text-slate-400
              "
            >
              응답{" "}
              {
                feedback
                  .selection_feedback
                  .feedback_count
              }
              건
            </div>


            {
              feedback
                .selection_feedback
                .feedback_count
              === 0
                ? (
                    <EmptyReason
                      text="아직 선택 이유 응답이 없습니다."
                    />
                  )

                : (
                    <div
                      className="
                        mt-5
                        space-y-4
                      "
                    >

                      {
                        feedback
                          .selection_feedback
                          .reasons
                          .map(
                            reason => (

                              <ReasonBar
                                key={
                                  reason.reason_code
                                }

                                label={
                                  REASON_LABELS[
                                    reason.reason_code
                                  ]
                                  ??
                                  reason.reason_code
                                }

                                value={
                                  reason
                                    .feedback_share_pct
                                }

                                count={
                                  reason.count
                                }
                              />

                            )
                          )
                      }

                    </div>
                  )
            }


            <p
              className="
                mt-5
                text-xs
                leading-5
                text-slate-400
              "
            >
              한 사용자가 여러 이유를 선택할 수 있어
              합계가 100%를 넘을 수 있습니다.
            </p>

          </div>


          {/* 비선택 이유 */}

          <div
            className="
              rounded-2xl
              border
              border-slate-200
              bg-white
              p-6
            "
          >

            <div
              className="
                text-xs
                font-bold
                text-slate-400
              "
            >
              왜 아무것도 선택하지 않았나?
            </div>


            <h2
              className="
                mt-1
                text-xl
                font-bold
              "
            >
              사용자가 직접 말한 이탈 이유
            </h2>


            <div
              className="
                mt-1
                text-xs
                text-slate-400
              "
            >
              응답{" "}
              {
                feedback
                  .no_selection_feedback
                  .feedback_count
              }
              건
            </div>


            {
              feedback
                .no_selection_feedback
                .feedback_count
              === 0

                ? (
                    <div
                      className="
                        mt-5
                        rounded-xl
                        bg-amber-50
                        p-5
                      "
                    >

                      <div
                        className="
                          font-bold
                          text-amber-800
                        "
                      >
                        아직 직접 이탈 이유가 없습니다.
                      </div>


                      <p
                        className="
                          mt-2
                          text-sm
                          leading-6
                          text-amber-700
                        "
                      >
                        현재는 이탈률이 높은 것은 알지만,
                        사용자가 왜 선택하지 않았는지는
                        아직 단정할 수 없습니다.
                      </p>

                    </div>
                  )

                : (
                    <div
                      className="
                        mt-5
                        space-y-4
                      "
                    >

                      {
                        feedback
                          .no_selection_feedback
                          .reasons
                          .map(
                            reason => (

                              <ReasonBar
                                key={
                                  reason.reason_code
                                }

                                label={
                                  REASON_LABELS[
                                    reason.reason_code
                                  ]
                                  ??
                                  reason.reason_code
                                }

                                value={
                                  reason
                                    .feedback_share_pct
                                }

                                count={
                                  reason.count
                                }
                              />

                            )
                          )
                      }

                    </div>
                  )
            }

          </div>

        </section>


        {/* =============================================
            병원별
        ============================================= */}

        <div
          className="
            mt-5
          "
        >

          <HospitalDecisionTable />

        </div>


        {/* =============================================
            개발자 정보는 숨김
        ============================================= */}

        <details
          className="
            mt-5
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-5
          "
        >

          <summary
            className="
              cursor-pointer
              font-bold
            "
          >
            개발자용 상세 데이터 보기
          </summary>


          <div
            className="
              mt-5
              grid
              gap-3
              md:grid-cols-3
            "
          >

            <DeveloperCard
              label="후보 노출 → 선택"
              value={
                `${
                  funnel
                    .conversion_rates_pct
                    .shown_to_selected
                }%`
              }
            />


            <DeveloperCard
              label="선택 → HOLD"
              value={
                `${
                  funnel
                    .conversion_rates_pct
                    .selected_to_held
                }%`
              }
            />


            <DeveloperCard
              label="전체 검색 → 예약"
              value={
                `${
                  funnel
                    .conversion_rates_pct
                    .search_to_confirmed
                }%`
              }
            />

          </div>

        </details>


        <div
          className="
            py-8
            text-center
            text-xs
            text-slate-400
          "
        >
          현재 숫자는 개발 과정에서 생성된
          합성 테스트 데이터입니다.
        </div>

      </div>

    </main>
  );
}


function SimpleNumber({
  label,
  value,
}: {
  label: string;
  value: number;
}) {

  return (
    <div
      className="
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-5
      "
    >

      <div
        className="
          text-sm
          text-slate-500
        "
      >
        {label}
      </div>


      <div
        className="
          mt-2
          text-4xl
          font-black
        "
      >
        {value}
        <span
          className="
            ml-1
            text-sm
            font-normal
            text-slate-400
          "
        >
          건
        </span>
      </div>

    </div>
  );
}


function ReasonBar({
  label,
  value,
  count,
}: {
  label: string;
  value: number;
  count: number;
}) {

  return (
    <div>

      <div
        className="
          mb-2
          flex
          items-center
          justify-between
          gap-4
        "
      >

        <strong
          className="
            text-sm
          "
        >
          {label}
        </strong>


        <span
          className="
            text-sm
            font-bold
          "
        >
          {value}%
        </span>

      </div>


      <div
        className="
          h-2
          overflow-hidden
          rounded-full
          bg-slate-100
        "
      >

        <div
          className="
            h-full
            bg-blue-500
          "

          style={{
            width:
              `${Math.min(
                value,
                100
              )}%`,
          }}
        />

      </div>


      <div
        className="
          mt-1
          text-right
          text-xs
          text-slate-400
        "
      >
        {count}건
      </div>

    </div>
  );
}


function EmptyReason({
  text,
}: {
  text: string;
}) {

  return (
    <div
      className="
        mt-5
        rounded-xl
        bg-slate-50
        p-5
        text-sm
        text-slate-500
      "
    >
      {text}
    </div>
  );
}


function DeveloperCard({
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
        p-4
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
          text-xl
          font-bold
        "
      >
        {value}
      </div>

    </div>
  );
}