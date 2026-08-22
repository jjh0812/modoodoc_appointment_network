"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";


type DecisionLossData = {
  hospital: {
    hospital_id: number;
    hospital_name: string;
    district: string;
  };

  decision_summary: {
    shown_intents: number;
    decision_opportunities: number;
    selected_by_this_hospital: number;
    lost_to_other_candidate: number;
    no_selection_after_exposure: number;
    decision_win_rate_pct: number;
  };

  loss_signal_counts: {
    not_top1: number;
    lower_rank_than_selected: number;
    lower_score_than_selected: number;
    budget_partial_match: number;
  };

  loss_signal_rates_pct: {
    not_top1: number;
    lower_rank_than_selected: number;
    lower_score_than_selected: number;
    budget_partial_match: number;
  };

  comparison: {
    average_rank_gap_on_losses: number;
    average_score_gap_on_losses: number;
  };

  lost_cases: Array<{
    intent_id: number;

    hospital_candidate: {
      candidate_match_id: number;
      rank: number | null;
      constraint_match_score: number;
      budget_status: string | null;
    };

    selected_candidate: {
      candidate_match_id: number;
      hospital_id: number;
      hospital_name: string;
      rank: number | null;
      constraint_match_score: number;
    };

    signals: string[];
  }>;

  note: string;
};


type Props = {
  hospitalId: number | null;
};


const API_BASE =
  "http://127.0.0.1:8001";


export default function HospitalDecisionLossPanel({
  hospitalId,
}: Props) {

  const [data, setData] =
    useState<DecisionLossData | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {

    if (hospitalId === null) {
      setData(null);
      return;
    }


    async function loadDecisionLoss() {

      try {

        setLoading(true);
        setError(null);


        const response =
          await fetch(
            `${API_BASE}/analytics/hospitals/${hospitalId}/decision-loss`,
            {
              cache: "no-store",
            }
          );


        if (!response.ok) {

          throw new Error(
            `Decision Loss API error: ${response.status}`
          );
        }


        const result: DecisionLossData =
          await response.json();


        setData(result);

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : "Unknown error"
        );

      } finally {

        setLoading(false);
      }
    }


    loadDecisionLoss();

  }, [hospitalId]);


  if (hospitalId === null) {

    return (
      <div style={styles.empty}>
        위 표에서 병원을 선택하면
        Decision Loss Signal을 볼 수 있습니다.
      </div>
    );
  }


  if (loading) {

    return (
      <div style={styles.loading}>
        Decision Loss 분석 중...
      </div>
    );
  }


  if (error || !data) {

    return (
      <div style={styles.error}>
        {error ?? "Decision Loss 데이터가 없습니다."}
      </div>
    );
  }


  const signals = [
    {
      key: "lower_score_than_selected",
      label: "선택된 후보보다 낮은 조건 일치 점수",
      value:
        data.loss_signal_rates_pct
          .lower_score_than_selected,
      count:
        data.loss_signal_counts
          .lower_score_than_selected,
    },
    {
      key: "lower_rank_than_selected",
      label: "선택된 후보보다 낮은 순위",
      value:
        data.loss_signal_rates_pct
          .lower_rank_than_selected,
      count:
        data.loss_signal_counts
          .lower_rank_than_selected,
    },
    {
      key: "not_top1",
      label: "Top-1 후보가 아니었음",
      value:
        data.loss_signal_rates_pct
          .not_top1,
      count:
        data.loss_signal_counts
          .not_top1,
    },
    {
      key: "budget_partial_match",
      label: "예산이 부분 일치였음",
      value:
        data.loss_signal_rates_pct
          .budget_partial_match,
      count:
        data.loss_signal_counts
          .budget_partial_match,
    },
  ];


  return (
    <div style={styles.wrapper}>

      {/* ============================================= */}
      {/* HEADER */}
      {/* ============================================= */}

      <div style={styles.header}>

        <div>

          <div style={styles.eyebrow}>
            DECISION LOSS SIGNALS
          </div>

          <h3 style={styles.title}>
            {data.hospital.hospital_name}
          </h3>

          <div style={styles.district}>
            {data.hospital.district}
          </div>

        </div>


        <div style={styles.winRateBox}>

          <span style={styles.smallLabel}>
            Decision Win Rate
          </span>

          <strong style={styles.winRate}>
            {
              data.decision_summary
                .decision_win_rate_pct
            }%
          </strong>

        </div>

      </div>


      {/* ============================================= */}
      {/* SUMMARY */}
      {/* ============================================= */}

      <div style={styles.summaryGrid}>

        <SummaryCard
          label="후보 노출"
          value={
            data.decision_summary
              .shown_intents
          }
          sub="Shown Intents"
        />

        <SummaryCard
          label="실제 선택 발생 상황"
          value={
            data.decision_summary
              .decision_opportunities
          }
          sub="Decision Opportunities"
        />

        <SummaryCard
          label="이 병원 선택"
          value={
            data.decision_summary
              .selected_by_this_hospital
          }
          sub="Won"
        />

        <SummaryCard
          label="다른 병원 선택"
          value={
            data.decision_summary
              .lost_to_other_candidate
          }
          sub="Lost"
        />

        <SummaryCard
          label="선택 없이 종료"
          value={
            data.decision_summary
              .no_selection_after_exposure
          }
          sub="No Selection"
        />

      </div>


      {/* ============================================= */}
      {/* LOSS SIGNALS */}
      {/* ============================================= */}

      <div style={styles.section}>

        <div style={styles.sectionHeader}>

          <div>

            <h4 style={styles.sectionTitle}>
              관측된 Loss Signals
            </h4>

            <p style={styles.sectionDescription}>
              다른 병원이 실제 선택된 경우에만 비교합니다.
            </p>

          </div>

        </div>


        <div style={styles.signalList}>

          {signals.map(
            (signal) => (

              <div
                key={signal.key}
                style={styles.signalRow}
              >

                <div style={styles.signalLabelArea}>

                  <strong>
                    {signal.label}
                  </strong>

                  <span style={styles.signalCount}>
                    {signal.count}건
                  </span>

                </div>


                <div style={styles.signalRight}>

                  <div style={styles.signalTrack}>

                    <div
                      style={{
                        ...styles.signalFill,
                        width:
                          `${signal.value}%`,
                      }}
                    />

                  </div>


                  <strong style={styles.signalPercent}>
                    {signal.value}%
                  </strong>

                </div>

              </div>

            )
          )}

        </div>

      </div>


      {/* ============================================= */}
      {/* COMPARISON */}
      {/* ============================================= */}

      <div style={styles.comparisonGrid}>

        <div style={styles.comparisonCard}>

          <div style={styles.comparisonLabel}>
            평균 순위 차이
          </div>

          <div style={styles.comparisonValue}>
            {
              data.comparison
                .average_rank_gap_on_losses
            }
          </div>

          <div style={styles.comparisonHint}>
            선택된 병원보다 평균 몇 순위 낮았는지
          </div>

        </div>


        <div style={styles.comparisonCard}>

          <div style={styles.comparisonLabel}>
            평균 조건 점수 차이
          </div>

          <div style={styles.comparisonValue}>
            {
              data.comparison
                .average_score_gap_on_losses
            }
          </div>

          <div style={styles.comparisonHint}>
            선택된 후보와의 constraint score 차이
          </div>

        </div>

      </div>


      {/* ============================================= */}
      {/* LOST CASES */}
      {/* ============================================= */}

      {data.lost_cases.length > 0 && (

        <div style={styles.section}>

          <h4 style={styles.sectionTitle}>
            비교 가능한 Loss Cases
          </h4>

          <p style={styles.sectionDescription}>
            실제로 다른 병원이 선택된 개별 Decision 사례입니다.
          </p>


          <div style={styles.caseList}>

            {data.lost_cases.map(
              (lossCase) => (

                <div
                  key={lossCase.intent_id}
                  style={styles.caseCard}
                >

                  <div style={styles.caseHeader}>

                    <strong>
                      Intent #{lossCase.intent_id}
                    </strong>

                    <span style={styles.caseSignalCount}>
                      {lossCase.signals.length} signals
                    </span>

                  </div>


                  <div style={styles.caseComparison}>

                    <div style={styles.caseSide}>

                      <span style={styles.caseSideTitle}>
                        이 병원
                      </span>

                      <strong>
                        Rank #
                        {
                          lossCase
                            .hospital_candidate
                            .rank
                          ?? "-"
                        }
                      </strong>

                      <span>
                        Score{" "}
                        {
                          lossCase
                            .hospital_candidate
                            .constraint_match_score
                        }
                      </span>

                      <span>
                        {
                          lossCase
                            .hospital_candidate
                            .budget_status
                          ?? "NO BUDGET STATUS"
                        }
                      </span>

                    </div>


                    <div style={styles.caseArrow}>
                      →
                    </div>


                    <div style={styles.caseSide}>

                      <span style={styles.caseSideTitle}>
                        실제 선택
                      </span>

                      <strong>
                        {
                          lossCase
                            .selected_candidate
                            .hospital_name
                        }
                      </strong>

                      <span>
                        Rank #
                        {
                          lossCase
                            .selected_candidate
                            .rank
                          ?? "-"
                        }
                      </span>

                      <span>
                        Score{" "}
                        {
                          lossCase
                            .selected_candidate
                            .constraint_match_score
                        }
                      </span>

                    </div>

                  </div>

                </div>

              )
            )}

          </div>

        </div>

      )}


      {/* ============================================= */}
      {/* CAUSALITY WARNING */}
      {/* ============================================= */}

      <div style={styles.warning}>

        <strong>
          해석 주의
        </strong>

        <p style={styles.warningText}>
          위 항목은 다른 후보가 선택된 순간에
          관측된 차이입니다.
          사용자가 실제로 그 이유 때문에
          해당 병원을 선택하지 않았다는
          인과관계를 증명하지는 않습니다.
        </p>

      </div>

    </div>
  );
}


function SummaryCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: number;
  sub: string;
}) {

  return (
    <div style={styles.summaryCard}>

      <div style={styles.summaryLabel}>
        {label}
      </div>

      <div style={styles.summaryValue}>
        {value}
      </div>

      <div style={styles.summarySub}>
        {sub}
      </div>

    </div>
  );
}


const styles: Record<string, CSSProperties> = {

  wrapper: {
    marginTop: "22px",
    borderTop: "1px solid #e5e7eb",
    paddingTop: "24px",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "20px",
    alignItems: "flex-start",
  },

  eyebrow: {
    fontSize: "10px",
    fontWeight: 800,
    letterSpacing: "0.15em",
    color: "#64748b",
    marginBottom: "8px",
  },

  title: {
    margin: 0,
    fontSize: "20px",
  },

  district: {
    marginTop: "6px",
    color: "#94a3b8",
    fontSize: "12px",
  },

  winRateBox: {
    minWidth: "130px",
    textAlign: "right",
  },

  smallLabel: {
    color: "#64748b",
    fontSize: "10px",
    display: "block",
  },

  winRate: {
    fontSize: "28px",
    marginTop: "5px",
    display: "block",
  },

  summaryGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "10px",
    marginTop: "20px",
  },

  summaryCard: {
    background: "#f8fafc",
    borderRadius: "11px",
    padding: "15px",
  },

  summaryLabel: {
    fontSize: "11px",
    color: "#64748b",
  },

  summaryValue: {
    fontSize: "24px",
    fontWeight: 800,
    marginTop: "6px",
  },

  summarySub: {
    color: "#94a3b8",
    fontSize: "9px",
    marginTop: "4px",
  },

  section: {
    marginTop: "24px",
  },

  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
  },

  sectionTitle: {
    margin: 0,
    fontSize: "15px",
  },

  sectionDescription: {
    marginTop: "5px",
    marginBottom: "14px",
    color: "#94a3b8",
    fontSize: "11px",
  },

  signalList: {
    display: "flex",
    flexDirection: "column",
  },

  signalRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    alignItems: "center",
    gap: "20px",
    padding: "12px 0",
    borderBottom: "1px solid #f1f5f9",
  },

  signalLabelArea: {
    display: "flex",
    justifyContent: "space-between",
    gap: "10px",
    fontSize: "12px",
  },

  signalCount: {
    color: "#94a3b8",
    fontWeight: 400,
  },

  signalRight: {
    display: "grid",
    gridTemplateColumns: "1fr 55px",
    alignItems: "center",
    gap: "12px",
  },

  signalTrack: {
    height: "8px",
    background: "#f1f5f9",
    borderRadius: "999px",
    overflow: "hidden",
  },

  signalFill: {
    height: "100%",
    background: "#cbd5e1",
    borderRadius: "999px",
  },

  signalPercent: {
    textAlign: "right",
    fontSize: "12px",
  },

  comparisonGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "12px",
    marginTop: "20px",
  },

  comparisonCard: {
    border: "1px solid #e5e7eb",
    borderRadius: "12px",
    padding: "16px",
  },

  comparisonLabel: {
    color: "#64748b",
    fontSize: "11px",
  },

  comparisonValue: {
    marginTop: "7px",
    fontSize: "25px",
    fontWeight: 800,
  },

  comparisonHint: {
    color: "#94a3b8",
    fontSize: "10px",
    marginTop: "6px",
  },

  caseList: {
    display: "grid",
    gap: "10px",
  },

  caseCard: {
    background: "#f8fafc",
    borderRadius: "12px",
    padding: "15px",
  },

  caseHeader: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "11px",
  },

  caseSignalCount: {
    color: "#94a3b8",
  },

  caseComparison: {
    marginTop: "12px",
    display: "grid",
    gridTemplateColumns: "1fr 30px 1fr",
    alignItems: "center",
    gap: "10px",
  },

  caseSide: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    fontSize: "11px",
  },

  caseSideTitle: {
    color: "#94a3b8",
    fontSize: "9px",
  },

  caseArrow: {
    textAlign: "center",
    color: "#94a3b8",
  },

  warning: {
    marginTop: "22px",
    padding: "15px",
    border: "1px solid #e5e7eb",
    borderRadius: "11px",
    background: "#fff",
    fontSize: "11px",
  },

  warningText: {
    color: "#64748b",
    lineHeight: 1.6,
    marginBottom: 0,
  },

  loading: {
    marginTop: "20px",
    padding: "18px",
    background: "#f8fafc",
    borderRadius: "12px",
    color: "#64748b",
    fontSize: "12px",
  },

  empty: {
    marginTop: "20px",
    padding: "18px",
    background: "#f8fafc",
    borderRadius: "12px",
    color: "#64748b",
    fontSize: "12px",
  },

  error: {
    marginTop: "20px",
    padding: "18px",
    background: "#fef2f2",
    borderRadius: "12px",
    color: "#991b1b",
    fontSize: "12px",
  },
};
