"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";


type Reason = {
  reason_code: string;
  count: number;
  feedback_share_pct: number;
};


type SelectionReasonData = {
  hospital_id: number;
  selection_feedback_count: number;
  reasons: Reason[];
  note: string;
};


type Props = {
  hospitalId: number | null;
};


const API_BASE =
  "http://127.0.0.1:8001";


const LABELS:
  Record<string, string> = {

    PRICE:
      "가격",

    AVAILABILITY:
      "예약 가능 시간",

    LOCATION:
      "위치",

    DATA_CONFIDENCE:
      "정보 신뢰도",

    OTHER:
      "기타",
  };


export default function HospitalSelectionReasons({
  hospitalId,
}: Props) {

  const [data, setData] =
    useState<SelectionReasonData | null>(
      null
    );

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(
      null
    );


  useEffect(() => {

    if (hospitalId === null) {

      setData(null);

      return;
    }


    async function loadData() {

      try {

        setLoading(true);
        setError(null);


        const response =
          await fetch(
            (
              `${API_BASE}`
              +
              `/analytics/hospitals/${hospitalId}/selection-reasons`
            ),
            {
              cache:
                "no-store",
            }
          );


        if (!response.ok) {

          throw new Error(
            `Selection Reasons API error: ${response.status}`
          );
        }


        const result:
          SelectionReasonData =
            await response.json();


        setData(
          result
        );

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : "Unknown error"
        );

      } finally {

        setLoading(
          false
        );
      }
    }


    loadData();

  }, [hospitalId]);


  if (hospitalId === null) {

    return null;
  }


  if (loading) {

    return (
      <div style={styles.stateBox}>
        Explicit Feedback를 불러오는 중...
      </div>
    );
  }


  if (error) {

    return (
      <div style={styles.errorBox}>
        {error}
      </div>
    );
  }


  if (!data) {

    return null;
  }


  return (
    <div style={styles.wrapper}>

      <div style={styles.eyebrow}>
        EXPLICIT USER FEEDBACK
      </div>


      <div style={styles.header}>

        <div>

          <h4 style={styles.title}>
            사용자가 직접 밝힌 선택 이유
          </h4>

          <p style={styles.description}>
            시스템 추론이 아니라,
            실제 사용자가 제출한 Selection Feedback입니다.
          </p>

        </div>


        <div style={styles.countBox}>

          <span style={styles.countLabel}>
            Feedback
          </span>

          <strong style={styles.countValue}>
            {
              data
                .selection_feedback_count
            }
          </strong>

        </div>

      </div>


      {
        data.selection_feedback_count
        === 0
          ? (
              <div style={styles.emptyBox}>

                아직 이 병원에 대한
                직접 선택 이유 Feedback이 없습니다.

              </div>
            )

          : (
              <div style={styles.reasonList}>

                {
                  data.reasons.map(
                    reason => (

                      <div
                        key={
                          reason.reason_code
                        }
                        style={styles.reasonRow}
                      >

                        <div>

                          <strong style={styles.reasonLabel}>
                            {
                              LABELS[
                                reason.reason_code
                              ]
                              ??
                              reason.reason_code
                            }
                          </strong>


                          <div style={styles.reasonCode}>
                            {
                              reason.reason_code
                            }
                          </div>

                        </div>


                        <div style={styles.reasonMetric}>

                          <div style={styles.track}>

                            <div
                              style={{
                                ...styles.fill,

                                width:
                                  `${Math.min(
                                    reason.feedback_share_pct,
                                    100
                                  )}%`,
                              }}
                            />

                          </div>


                          <strong style={styles.percent}>
                            {
                              reason
                                .feedback_share_pct
                            }%
                          </strong>


                          <span style={styles.count}>
                            {reason.count}건
                          </span>

                        </div>

                      </div>

                    )
                  )
                }

              </div>
            )
      }


      <div style={styles.note}>

        복수 이유 선택이 가능하므로
        각 비율의 합계가 100%를 넘을 수 있습니다.

      </div>

    </div>
  );
}


const styles: Record<
  string,
  CSSProperties
> = {

  wrapper: {
    marginTop: "24px",
    borderTop:
      "1px solid #e5e7eb",
    paddingTop: "24px",
  },

  eyebrow: {
    fontSize: "10px",
    fontWeight: 800,
    letterSpacing: "0.15em",
    color: "#64748b",
    marginBottom: "8px",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "20px",
    alignItems: "flex-start",
  },

  title: {
    margin: 0,
    fontSize: "15px",
  },

  description: {
    marginTop: "6px",
    color: "#94a3b8",
    fontSize: "11px",
  },

  countBox: {
    minWidth: "75px",
    textAlign: "right",
  },

  countLabel: {
    display: "block",
    color: "#94a3b8",
    fontSize: "9px",
  },

  countValue: {
    display: "block",
    marginTop: "4px",
    fontSize: "24px",
  },

  reasonList: {
    marginTop: "18px",
  },

  reasonRow: {
    display: "grid",
    gridTemplateColumns:
      "180px 1fr",
    gap: "20px",
    alignItems: "center",
    padding: "13px 0",
    borderBottom:
      "1px solid #f1f5f9",
  },

  reasonLabel: {
    fontSize: "12px",
  },

  reasonCode: {
    marginTop: "3px",
    fontFamily: "monospace",
    color: "#94a3b8",
    fontSize: "9px",
  },

  reasonMetric: {
    display: "grid",
    gridTemplateColumns:
      "1fr 55px 35px",
    gap: "10px",
    alignItems: "center",
  },

  track: {
    height: "8px",
    borderRadius: "999px",
    background: "#f1f5f9",
    overflow: "hidden",
  },

  fill: {
    height: "100%",
    borderRadius: "999px",
    background: "#c4b5fd",
  },

  percent: {
    textAlign: "right",
    fontSize: "12px",
  },

  count: {
    color: "#94a3b8",
    fontSize: "10px",
    textAlign: "right",
  },

  emptyBox: {
    marginTop: "16px",
    borderRadius: "10px",
    background: "#f8fafc",
    padding: "15px",
    color: "#64748b",
    fontSize: "11px",
  },

  note: {
    marginTop: "13px",
    color: "#94a3b8",
    fontSize: "10px",
  },

  stateBox: {
    marginTop: "20px",
    color: "#64748b",
    fontSize: "11px",
  },

  errorBox: {
    marginTop: "20px",
    color: "#991b1b",
    fontSize: "11px",
  },
};
