"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

import HospitalDecisionLossPanel from "./HospitalDecisionLossPanel";


type HospitalAnalytics = {
  hospital_id: number;
  hospital_name: string;
  district: string;

  funnel: {
    shown: number;
    selected: number;
    held: number;
    confirmed: number;
  };

  conversion_rates_pct: {
    shown_to_selected: number;
    selected_to_held: number;
    held_to_confirmed: number;
    shown_to_confirmed: number;
  };

  ranking: {
    top1_shown: number;
    top1_share_pct: number;
    average_shown_rank: number | null;
  };

  event_counts: {
    shown: number;
    selected: number;
    held: number;
    confirmed: number;
  };
};


type HospitalAnalyticsResponse = {
  hospital_count: number;
  hospitals: HospitalAnalytics[];
  note: string;
};


const API_URL =
  "http://127.0.0.1:8001/analytics/hospitals";


export default function HospitalDecisionTable() {

  const [data, setData] =
    useState<HospitalAnalyticsResponse | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [selectedHospitalId, setSelectedHospitalId] =
    useState<number | null>(null);


  useEffect(() => {

    async function loadData() {

      try {

        setLoading(true);
        setError(null);


        const response =
          await fetch(
            API_URL,
            {
              cache: "no-store",
            }
          );


        if (!response.ok) {

          throw new Error(
            `Hospital analytics API error: ${response.status}`
          );
        }


        const result:
          HospitalAnalyticsResponse =
            await response.json();


        setData(result);


        if (
          result.hospitals.length > 0
        ) {

          setSelectedHospitalId(
            result.hospitals[0].hospital_id
          );
        }

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


    loadData();

  }, []);


  if (loading) {

    return (
      <section style={styles.panel}>
        병원별 Decision Intelligence를
        불러오는 중...
      </section>
    );
  }


  if (error || !data) {

    return (
      <section style={styles.panel}>

        <strong>
          Hospital Analytics 연결 실패
        </strong>

        <p style={styles.muted}>
          {error ?? "데이터가 없습니다."}
        </p>

      </section>
    );
  }


  return (
    <section style={styles.panel}>

      {/* ============================================= */}
      {/* HEADER */}
      {/* ============================================= */}

      <div style={styles.header}>

        <div>

          <div style={styles.eyebrow}>
            PROVIDER DECISION INTELLIGENCE
          </div>

          <h2 style={styles.title}>
            병원별 AI 노출 → 선택 → 예약
          </h2>

          <p style={styles.description}>
            병원 행을 클릭하면 실제 선택 경쟁에서
            어떤 Loss Signal이 관측됐는지 볼 수 있습니다.
          </p>

        </div>


        <div style={styles.countBadge}>
          {data.hospital_count} hospitals
        </div>

      </div>


      {/* ============================================= */}
      {/* TABLE */}
      {/* ============================================= */}

      <div style={styles.tableWrapper}>

        <table style={styles.table}>

          <thead>

            <tr>

              <th style={styles.leftHeader}>
                병원
              </th>

              <th style={styles.headerCell}>
                노출
              </th>

              <th style={styles.headerCell}>
                선택
              </th>

              <th style={styles.headerCell}>
                HOLD
              </th>

              <th style={styles.headerCell}>
                예약
              </th>

              <th style={styles.headerCell}>
                노출→선택
              </th>

              <th style={styles.headerCell}>
                노출→예약
              </th>

              <th style={styles.headerCell}>
                Top-1 노출
              </th>

              <th style={styles.headerCell}>
                평균 순위
              </th>

            </tr>

          </thead>


          <tbody>

            {data.hospitals.map(
              (
                hospital,
                index
              ) => {

                const selected =
                  selectedHospitalId
                  === hospital.hospital_id;


                return (

                  <tr
                    key={
                      hospital.hospital_id
                    }
                    onClick={() =>
                      setSelectedHospitalId(
                        hospital.hospital_id
                      )
                    }
                    style={{
                      ...styles.row,
                      ...(selected
                        ? styles.selectedRow
                        : {}),
                    }}
                  >

                    <td style={styles.hospitalCell}>

                      <div
                        style={{
                          ...styles.rankNumber,
                          ...(selected
                            ? styles.selectedRank
                            : {}),
                        }}
                      >
                        #{index + 1}
                      </div>


                      <div>

                        <strong>
                          {
                            hospital
                              .hospital_name
                          }
                        </strong>

                        <div style={styles.district}>
                          {hospital.district}
                        </div>

                      </div>

                    </td>


                    <td style={styles.numberCell}>
                      {hospital.funnel.shown}
                    </td>


                    <td style={styles.numberCell}>
                      {hospital.funnel.selected}
                    </td>


                    <td style={styles.numberCell}>
                      {hospital.funnel.held}
                    </td>


                    <td style={styles.numberCell}>
                      {hospital.funnel.confirmed}
                    </td>


                    <td style={styles.numberCell}>
                      {
                        hospital
                          .conversion_rates_pct
                          .shown_to_selected
                      }%
                    </td>


                    <td style={styles.numberCell}>
                      {
                        hospital
                          .conversion_rates_pct
                          .shown_to_confirmed
                      }%
                    </td>


                    <td style={styles.numberCell}>

                      <div>
                        {
                          hospital
                            .ranking
                            .top1_shown
                        }
                      </div>

                      <div style={styles.small}>
                        {
                          hospital
                            .ranking
                            .top1_share_pct
                        }%
                      </div>

                    </td>


                    <td style={styles.numberCell}>
                      {
                        hospital
                          .ranking
                          .average_shown_rank
                        ?? "-"
                      }
                    </td>

                  </tr>

                );
              }
            )}

          </tbody>

        </table>

      </div>


      <div style={styles.clickHint}>
        ↑ 병원을 클릭하면 아래 분석이 변경됩니다.
      </div>


      {/* ============================================= */}
      {/* DECISION LOSS */}
      {/* ============================================= */}

      <HospitalDecisionLossPanel
        hospitalId={
          selectedHospitalId
        }
      />


      {/* ============================================= */}
      {/* PROTOTYPE NOTICE */}
      {/* ============================================= */}

      <div style={styles.insightBox}>

        <strong>
          현재 데이터 해석
        </strong>

        <p style={styles.insightText}>
          기존 E2E 테스트가 대부분 1위 후보를
          자동 선택했기 때문에 현재 선택 데이터는
          실제 환자 선호를 의미하지 않습니다.
        </p>

        <p style={styles.insightText}>
          현재 목적은 병원별 노출, 선택, 거래,
          Loss Signal 분석 파이프라인이
          정상 연결되는지 검증하는 것입니다.
        </p>

      </div>


      <div style={styles.questionGrid}>

        <QuestionCard
          title="Exposure"
          text="AI가 우리 병원을 몇 번 후보로 보여줬나?"
        />

        <QuestionCard
          title="Selection"
          text="경쟁 후보 중 실제로 몇 번 선택됐나?"
        />

        <QuestionCard
          title="Conversion"
          text="선택이 HOLD와 예약으로 얼마나 이어졌나?"
        />

        <QuestionCard
          title="Loss Signals"
          text="다른 병원이 선택된 순간 어떤 차이가 있었나?"
        />

      </div>

    </section>
  );
}


function QuestionCard({
  title,
  text,
}: {
  title: string;
  text: string;
}) {

  return (
    <div style={styles.questionCard}>

      <div style={styles.questionTitle}>
        {title}
      </div>

      <div style={styles.questionText}>
        {text}
      </div>

    </div>
  );
}


const styles: Record<string, CSSProperties> = {

  panel: {
    maxWidth: "1400px",
    margin: "0 auto 20px auto",
    background: "#ffffff",
    border: "1px solid #e4e7ec",
    borderRadius: "16px",
    padding: "24px",
    color: "#111827",
    fontFamily:
      "Arial, Helvetica, sans-serif",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "20px",
  },

  eyebrow: {
    fontSize: "11px",
    fontWeight: 800,
    letterSpacing: "0.16em",
    color: "#64748b",
    marginBottom: "10px",
  },

  title: {
    margin: 0,
    fontSize: "20px",
    letterSpacing: "-0.02em",
  },

  description: {
    marginTop: "8px",
    color: "#64748b",
    fontSize: "13px",
  },

  countBadge: {
    padding: "8px 12px",
    border: "1px solid #e2e8f0",
    borderRadius: "999px",
    fontSize: "11px",
    fontWeight: 700,
    whiteSpace: "nowrap",
  },

  tableWrapper: {
    width: "100%",
    overflowX: "auto",
    marginTop: "22px",
  },

  table: {
    width: "100%",
    minWidth: "1000px",
    borderCollapse: "collapse",
  },

  leftHeader: {
    textAlign: "left",
    padding: "13px",
    borderBottom: "1px solid #e5e7eb",
    color: "#64748b",
    fontSize: "11px",
  },

  headerCell: {
    textAlign: "right",
    padding: "13px",
    borderBottom: "1px solid #e5e7eb",
    color: "#64748b",
    fontSize: "11px",
    whiteSpace: "nowrap",
  },

  row: {
    borderBottom: "1px solid #f1f5f9",
    cursor: "pointer",
    transition: "background 0.15s ease",
  },

  selectedRow: {
    background: "#f8fafc",
  },

  hospitalCell: {
    padding: "17px 13px",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    minWidth: "240px",
  },

  rankNumber: {
    width: "34px",
    height: "34px",
    borderRadius: "9px",
    background: "#f1f5f9",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 800,
    fontSize: "12px",
  },

  selectedRank: {
    background: "#e2e8f0",
  },

  district: {
    marginTop: "5px",
    color: "#94a3b8",
    fontSize: "11px",
  },

  numberCell: {
    padding: "17px 13px",
    textAlign: "right",
    fontWeight: 700,
    fontSize: "13px",
    whiteSpace: "nowrap",
  },

  small: {
    marginTop: "4px",
    color: "#94a3b8",
    fontWeight: 400,
    fontSize: "10px",
  },

  clickHint: {
    marginTop: "9px",
    color: "#94a3b8",
    fontSize: "10px",
  },

  insightBox: {
    marginTop: "22px",
    padding: "18px",
    borderRadius: "12px",
    background: "#f8fafc",
    fontSize: "13px",
  },

  insightText: {
    color: "#64748b",
    lineHeight: 1.7,
    marginBottom: 0,
  },

  questionGrid: {
    marginTop: "16px",
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(190px, 1fr))",
    gap: "12px",
  },

  questionCard: {
    padding: "16px",
    border: "1px solid #e5e7eb",
    borderRadius: "12px",
  },

  questionTitle: {
    fontSize: "11px",
    fontWeight: 800,
    letterSpacing: "0.08em",
  },

  questionText: {
    marginTop: "8px",
    color: "#64748b",
    fontSize: "12px",
    lineHeight: 1.5,
  },

  muted: {
    color: "#64748b",
  },
};
