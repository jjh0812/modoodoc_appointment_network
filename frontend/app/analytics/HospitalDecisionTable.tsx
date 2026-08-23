"use client";

import {
  useEffect,
  useState,
} from "react";

import type {
  CSSProperties,
} from "react";

import HospitalDecisionLossPanel
  from "./HospitalDecisionLossPanel";

import HospitalSelectionReasons
  from "./HospitalSelectionReasons";


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
    average_shown_rank:
      number | null;
  };

  event_counts: {
    shown: number;
    selected: number;
    held: number;
    confirmed: number;
  };
};


type HospitalResponse = {
  hospital_count: number;
  hospitals:
    HospitalAnalytics[];
  note: string;
};


type LossData = {
  decision_summary: {
    shown_intents: number;
    decision_opportunities: number;
    selected_by_this_hospital: number;
    lost_to_other_candidate: number;
    no_selection_after_exposure: number;
    decision_win_rate_pct: number;
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
};


const API_BASE =
  "http://127.0.0.1:8001";


export default function HospitalDecisionTable() {

  const [
    data,
    setData,
  ] = useState<HospitalResponse | null>(
    null
  );


  const [
    selectedHospitalId,
    setSelectedHospitalId,
  ] = useState<number | null>(
    null
  );


  const [
    selectedLoss,
    setSelectedLoss,
  ] = useState<LossData | null>(
    null
  );


  const [
    loading,
    setLoading,
  ] = useState(
    true
  );


  useEffect(() => {

    async function loadHospitals() {

      const response =
        await fetch(
          `${API_BASE}/analytics/hospitals`,
          {
            cache:
              "no-store",
          }
        );


      const result:
        HospitalResponse =
          await response.json();


      setData(
        result
      );


      if (
        result.hospitals.length
        > 0
      ) {

        setSelectedHospitalId(
          result
            .hospitals[0]
            .hospital_id
        );
      }


      setLoading(
        false
      );
    }


    loadHospitals();

  }, []);


  useEffect(() => {

    if (
      selectedHospitalId
      === null
    ) {

      setSelectedLoss(
        null
      );

      return;
    }


    async function loadLoss() {

      const response =
        await fetch(
          (
            `${API_BASE}`
            +
            `/analytics/hospitals/${selectedHospitalId}/decision-loss`
          ),
          {
            cache:
              "no-store",
          }
        );


      if (!response.ok) {

        setSelectedLoss(
          null
        );

        return;
      }


      const result:
        LossData =
          await response.json();


      setSelectedLoss(
        result
      );
    }


    loadLoss();

  }, [selectedHospitalId]);


  if (
    loading
    ||
    !data
  ) {

    return (
      <section style={styles.panel}>
        병원 데이터를 불러오는 중...
      </section>
    );
  }


  const selectedHospital =
    data.hospitals.find(
      hospital =>
        hospital.hospital_id
        === selectedHospitalId
    )
    ??
    null;


  return (
    <section style={styles.panel}>

      {/* ============================================= */}
      {/* HEADER */}
      {/* ============================================= */}

      <div style={styles.header}>

        <div>

          <div style={styles.eyebrow}>
            HOSPITAL PERFORMANCE
          </div>

          <h2 style={styles.title}>
            어느 병원이 선택되고 있는가?
          </h2>

          <p style={styles.description}>
            복잡한 원본 지표 대신
            노출·선택·예약과
            가장 중요한 관측 신호만 보여줍니다.
          </p>

        </div>

      </div>


      {/* ============================================= */}
      {/* SIMPLE TABLE */}
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
                선택률
              </th>

              <th style={styles.headerCell}>
                예약률
              </th>

              <th style={styles.leftHeader}>
                한눈에 보는 상태
              </th>

            </tr>

          </thead>


          <tbody>

            {
              data.hospitals.map(
                hospital => {

                  const selected =
                    hospital.hospital_id
                    === selectedHospitalId;


                  return (
                    <tr
                      key={
                        hospital.hospital_id
                      }

                      onClick={
                        () =>
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

                        <strong>
                          {
                            hospital
                              .hospital_name
                          }
                        </strong>

                        <span style={styles.district}>
                          {hospital.district}
                        </span>

                      </td>


                      <td style={styles.numberCell}>
                        {
                          hospital
                            .funnel
                            .shown
                        }
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


                      <td style={styles.statusCell}>
                        <HospitalStatus
                          hospital={
                            hospital
                          }
                        />
                      </td>

                    </tr>
                  );
                }
              )
            }

          </tbody>

        </table>

      </div>


      {/* ============================================= */}
      {/* SELECTED HOSPITAL QUICK READ */}
      {/* ============================================= */}

      {
        selectedHospital
        &&
        (
          <div style={styles.quickPanel}>

            <div style={styles.quickHeader}>

              <div>

                <div style={styles.eyebrow}>
                  QUICK READ
                </div>

                <h3 style={styles.quickTitle}>
                  {
                    selectedHospital
                      .hospital_name
                  }
                </h3>

              </div>


              <div style={styles.quickRate}>

                <span style={styles.rateLabel}>
                  선택률
                </span>

                <strong style={styles.rateValue}>
                  {
                    selectedHospital
                      .conversion_rates_pct
                      .shown_to_selected
                  }%
                </strong>

              </div>

            </div>


            <div style={styles.quickGrid}>

              <QuickCard
                label="후보 노출"
                value={
                  `${selectedHospital
                    .funnel
                    .shown}건`
                }
              />

              <QuickCard
                label="실제 선택"
                value={
                  `${selectedHospital
                    .funnel
                    .selected}건`
                }
              />

              <QuickCard
                label="예약 확정"
                value={
                  `${selectedHospital
                    .funnel
                    .confirmed}건`
                }
              />

            </div>


            {
              selectedLoss
              &&
              (
                <div style={styles.diagnosisBox}>

                  <strong>
                    선택 경쟁에서 반복적으로 관측된 차이
                  </strong>


                  <div style={styles.diagnosisList}>

                    {
                      selectedLoss
                        .loss_signal_rates_pct
                        .budget_partial_match
                      > 0
                      &&
                      (
                        <DiagnosisItem>
                          예산 부분 일치가{" "}
                          {
                            selectedLoss
                              .loss_signal_rates_pct
                              .budget_partial_match
                          }
                          %의 비교 상황에서 관측됨
                        </DiagnosisItem>
                      )
                    }


                    {
                      selectedLoss
                        .comparison
                        .average_score_gap_on_losses
                      > 0
                      &&
                      (
                        <DiagnosisItem>
                          선택된 병원보다 조건 점수가
                          평균{" "}
                          <strong>
                            {
                              selectedLoss
                                .comparison
                                .average_score_gap_on_losses
                            }
                            점 낮았음
                          </strong>
                        </DiagnosisItem>
                      )
                    }


                    {
                      selectedLoss
                        .comparison
                        .average_rank_gap_on_losses
                      > 0
                      &&
                      (
                        <DiagnosisItem>
                          선택된 병원보다 평균{" "}
                          <strong>
                            {
                              selectedLoss
                                .comparison
                                .average_rank_gap_on_losses
                            }
                            단계 낮게 노출
                          </strong>
                        </DiagnosisItem>
                      )
                    }


                    {
                      selectedLoss
                        .decision_summary
                        .decision_opportunities
                      === 0
                      &&
                      (
                        <DiagnosisItem>
                          아직 실제 선택 경쟁 데이터가
                          충분하지 않습니다.
                        </DiagnosisItem>
                      )
                    }

                  </div>


                  <div style={styles.causalityNote}>
                    위 항목은 관측된 차이이며
                    실제 선택 원인을 증명하지는 않습니다.
                  </div>

                </div>
              )
            }


            {/* ========================================= */}
            {/* EXPLICIT FEEDBACK */}
            {/* ========================================= */}

            <HospitalSelectionReasons
              hospitalId={
                selectedHospitalId
              }
            />


            {/* ========================================= */}
            {/* RAW DETAIL */}
            {/* ========================================= */}

            <details style={styles.detailBox}>

              <summary style={styles.detailSummary}>
                근거 데이터 자세히 보기
              </summary>


              <HospitalDecisionLossPanel
                hospitalId={
                  selectedHospitalId
                }
              />

            </details>

          </div>
        )
      }

    </section>
  );
}


function HospitalStatus({
  hospital,
}: {
  hospital: HospitalAnalytics;
}) {

  if (
    hospital.funnel.confirmed
    > 0
  ) {

    return (
      <span style={styles.goodStatus}>
        예약 {hospital.funnel.confirmed}건 발생
      </span>
    );
  }


  if (
    hospital.funnel.selected
    > 0
  ) {

    return (
      <span style={styles.neutralStatus}>
        선택은 발생했지만 예약 0건
      </span>
    );
  }


  if (
    hospital
      .ranking
      .average_shown_rank
    !== null
  ) {

    return (
      <span style={styles.neutralStatus}>
        평균{" "}
        {
          hospital
            .ranking
            .average_shown_rank
        }
        위 노출 · 선택 0건
      </span>
    );
  }


  return (
    <span style={styles.neutralStatus}>
      데이터 부족
    </span>
  );
}


function QuickCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {

  return (
    <div style={styles.quickCard}>

      <div style={styles.quickLabel}>
        {label}
      </div>

      <strong style={styles.quickValue}>
        {value}
      </strong>

    </div>
  );
}


function DiagnosisItem({
  children,
}: {
  children:
    React.ReactNode;
}) {

  return (
    <div style={styles.diagnosisItem}>
      • {children}
    </div>
  );
}


const styles:
  Record<string, CSSProperties> = {

  panel: {
    background:
      "#ffffff",

    border:
      "1px solid #e5e7eb",

    borderRadius:
      "16px",

    padding:
      "24px",

    marginBottom:
      "18px",
  },

  header: {
    display:
      "flex",

    justifyContent:
      "space-between",

    gap:
      "20px",
  },

  eyebrow: {
    color:
      "#64748b",

    fontSize:
      "10px",

    fontWeight:
      800,

    letterSpacing:
      "0.14em",
  },

  title: {
    margin:
      "7px 0 0 0",

    fontSize:
      "19px",
  },

  description: {
    marginTop:
      "7px",

    color:
      "#94a3b8",

    fontSize:
      "12px",
  },

  tableWrapper: {
    width:
      "100%",

    overflowX:
      "auto",

    marginTop:
      "20px",
  },

  table: {
    width:
      "100%",

    borderCollapse:
      "collapse",

    minWidth:
      "760px",
  },

  leftHeader: {
    textAlign:
      "left",

    padding:
      "12px",

    borderBottom:
      "1px solid #e5e7eb",

    color:
      "#64748b",

    fontSize:
      "10px",
  },

  headerCell: {
    textAlign:
      "right",

    padding:
      "12px",

    borderBottom:
      "1px solid #e5e7eb",

    color:
      "#64748b",

    fontSize:
      "10px",
  },

  row: {
    cursor:
      "pointer",

    borderBottom:
      "1px solid #f1f5f9",
  },

  selectedRow: {
    background:
      "#f8fafc",
  },

  hospitalCell: {
    padding:
      "16px 12px",

    display:
      "flex",

    flexDirection:
      "column",

    gap:
      "4px",
  },

  district: {
    color:
      "#94a3b8",

    fontSize:
      "10px",
  },

  numberCell: {
    padding:
      "16px 12px",

    textAlign:
      "right",

    fontWeight:
      700,

    fontSize:
      "13px",
  },

  statusCell: {
    padding:
      "16px 12px",

    minWidth:
      "200px",
  },

  goodStatus: {
    color:
      "#047857",

    fontSize:
      "12px",

    fontWeight:
      700,
  },

  neutralStatus: {
    color:
      "#64748b",

    fontSize:
      "12px",
  },

  quickPanel: {
    marginTop:
      "24px",

    borderTop:
      "1px solid #e5e7eb",

    paddingTop:
      "24px",
  },

  quickHeader: {
    display:
      "flex",

    justifyContent:
      "space-between",

    gap:
      "20px",
  },

  quickTitle: {
    margin:
      "7px 0 0 0",

    fontSize:
      "20px",
  },

  quickRate: {
    textAlign:
      "right",
  },

  rateLabel: {
    display:
      "block",

    color:
      "#94a3b8",

    fontSize:
      "9px",
  },

  rateValue: {
    display:
      "block",

    marginTop:
      "3px",

    fontSize:
      "28px",
  },

  quickGrid: {
    display:
      "grid",

    gridTemplateColumns:
      "repeat(auto-fit, minmax(150px, 1fr))",

    gap:
      "10px",

    marginTop:
      "18px",
  },

  quickCard: {
    padding:
      "15px",

    background:
      "#f8fafc",

    borderRadius:
      "11px",
  },

  quickLabel: {
    color:
      "#64748b",

    fontSize:
      "10px",
  },

  quickValue: {
    display:
      "block",

    marginTop:
      "5px",

    fontSize:
      "23px",
  },

  diagnosisBox: {
    marginTop:
      "18px",

    padding:
      "17px",

    borderRadius:
      "12px",

    background:
      "#fff7ed",

    fontSize:
      "12px",
  },

  diagnosisList: {
    marginTop:
      "10px",

    display:
      "flex",

    flexDirection:
      "column",

    gap:
      "7px",
  },

  diagnosisItem: {
    color:
      "#475569",

    lineHeight:
      1.6,
  },

  causalityNote: {
    marginTop:
      "11px",

    color:
      "#94a3b8",

    fontSize:
      "9px",
  },

  detailBox: {
    marginTop:
      "22px",

    border:
      "1px solid #e5e7eb",

    borderRadius:
      "12px",

    padding:
      "14px",
  },

  detailSummary: {
    cursor:
      "pointer",

    fontSize:
      "12px",

    fontWeight:
      700,
  },
};