"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

import HospitalDecisionTable from "./HospitalDecisionTable";


type Funnel = {
  searched: number;
  shown: number;
  selected: number;
  held: number;
  confirmed: number;
};


type ConversionRates = {
  search_to_shown: number;
  shown_to_selected: number;
  selected_to_held: number;
  held_to_confirmed: number;
  search_to_confirmed: number;
};


type EventCounts = {
  shown: number;
  selected: number;
  held: number;
  confirmed: number;
};


type AnalyticsData = {
  funnel: Funnel;
  conversion_rates_pct: ConversionRates;
  event_counts: EventCounts;
  searches_by_source: Record<string, number>;
};


const API_URL =
  "http://127.0.0.1:8001/analytics/decision-funnel";


export default function AnalyticsPage() {

  const [data, setData] =
    useState<AnalyticsData | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {

    async function loadAnalytics() {

      try {

        setLoading(true);
        setError(null);


        const response = await fetch(
          API_URL,
          {
            cache: "no-store",
          }
        );


        if (!response.ok) {

          throw new Error(
            `Analytics API error: ${response.status}`
          );
        }


        const result: AnalyticsData =
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


    loadAnalytics();

  }, []);


  if (loading) {

    return (
      <main style={styles.page}>
        <div style={styles.loadingCard}>
          Analytics 데이터를 불러오는 중...
        </div>
      </main>
    );
  }


  if (error || !data) {

    return (
      <main style={styles.page}>

        <div style={styles.errorCard}>

          <h1 style={styles.errorTitle}>
            Analytics 연결 실패
          </h1>

          <p>
            {error ?? "데이터가 없습니다."}
          </p>

          <p style={styles.muted}>
            FastAPI가 127.0.0.1:8001에서
            실행 중인지 확인하세요.
          </p>

        </div>

      </main>
    );
  }


  const stages = [
    {
      label: "SEARCHED",
      korean: "검색",
      value: data.funnel.searched,
    },
    {
      label: "SHOWN",
      korean: "후보 노출",
      value: data.funnel.shown,
    },
    {
      label: "SELECTED",
      korean: "선택",
      value: data.funnel.selected,
    },
    {
      label: "HELD",
      korean: "HOLD",
      value: data.funnel.held,
    },
    {
      label: "CONFIRMED",
      korean: "예약 확정",
      value: data.funnel.confirmed,
    },
  ];


  const maxFunnel =
    Math.max(
      data.funnel.searched,
      1
    );


  return (
    <main style={styles.page}>

      {/* ================================================= */}
      {/* HEADER */}
      {/* ================================================= */}

      <header style={styles.header}>

        <div>

          <div style={styles.eyebrow}>
            MODOODOC EXECUTABLE DECISION NETWORK
          </div>

          <h1 style={styles.title}>
            Decision Analytics
          </h1>

          <p style={styles.subtitle}>
            환자의 검색이 어떤 후보 노출과 선택을 거쳐
            실제 예약으로 이어지는지 추적합니다.
          </p>

        </div>


        <div style={styles.liveBadge}>
          PROTOTYPE DATA
        </div>

      </header>


      {/* ================================================= */}
      {/* KPI */}
      {/* ================================================= */}

      <section style={styles.kpiGrid}>

        <KpiCard
          label="총 검색"
          value={data.funnel.searched}
          description="Patient Intent"
        />

        <KpiCard
          label="후보를 받은 검색"
          value={data.funnel.shown}
          description={
            `${data.conversion_rates_pct.search_to_shown}% of searches`
          }
        />

        <KpiCard
          label="후보 선택"
          value={data.funnel.selected}
          description={
            `${data.conversion_rates_pct.shown_to_selected}% of shown`
          }
        />

        <KpiCard
          label="예약 확정"
          value={data.funnel.confirmed}
          description={
            `${data.conversion_rates_pct.search_to_confirmed}% of searches`
          }
        />

      </section>


      {/* ================================================= */}
      {/* FUNNEL */}
      {/* ================================================= */}

      <section style={styles.panel}>

        <div style={styles.panelHeader}>

          <div>

            <h2 style={styles.panelTitle}>
              Decision Funnel
            </h2>

            <p style={styles.panelDescription}>
              각 단계는 중복 이벤트 수가 아니라
              Unique Patient Intent 기준입니다.
            </p>

          </div>

        </div>


        <div style={styles.funnelList}>

          {stages.map(
            (stage) => {

              const width =
                Math.max(
                  5,
                  (
                    stage.value
                    / maxFunnel
                  )
                  * 100
                );


              return (
                <div
                  key={stage.label}
                  style={styles.funnelRow}
                >

                  <div style={styles.funnelLabel}>

                    <strong>
                      {stage.korean}
                    </strong>

                    <span style={styles.funnelCode}>
                      {stage.label}
                    </span>

                  </div>


                  <div style={styles.barTrack}>

                    <div
                      style={{
                        ...styles.barFill,
                        width: `${width}%`,
                      }}
                    >

                      <strong>
                        {stage.value}
                      </strong>

                    </div>

                  </div>

                </div>
              );
            }
          )}

        </div>

      </section>


      {/* ================================================= */}
      {/* CONVERSION + SOURCE */}
      {/* ================================================= */}

      <section style={styles.twoColumn}>

        <div style={styles.panel}>

          <h2 style={styles.panelTitle}>
            Conversion Rates
          </h2>

          <p style={styles.panelDescription}>
            Decision Graph 단계별 전환
          </p>


          <MetricRow
            label="검색 → 후보 노출"
            value={
              data.conversion_rates_pct
                .search_to_shown
            }
          />

          <MetricRow
            label="후보 노출 → 선택"
            value={
              data.conversion_rates_pct
                .shown_to_selected
            }
          />

          <MetricRow
            label="선택 → HOLD"
            value={
              data.conversion_rates_pct
                .selected_to_held
            }
          />

          <MetricRow
            label="HOLD → 예약 확정"
            value={
              data.conversion_rates_pct
                .held_to_confirmed
            }
          />


          <div style={styles.finalConversion}>

            <span>
              전체 검색 → 최종 예약
            </span>

            <strong style={styles.finalRate}>
              {
                data.conversion_rates_pct
                  .search_to_confirmed
              }%
            </strong>

          </div>

        </div>


        <div style={styles.panel}>

          <h2 style={styles.panelTitle}>
            Search Sources
          </h2>

          <p style={styles.panelDescription}>
            Patient Intent가 들어온 채널
          </p>


          <div style={styles.sourceList}>

            {Object.entries(
              data.searches_by_source
            ).map(
              ([source, count]) => (

                <div
                  key={source}
                  style={styles.sourceRow}
                >

                  <div>

                    <div style={styles.sourceName}>
                      {source}
                    </div>

                    <div style={styles.sourceHint}>
                      Intent source
                    </div>

                  </div>


                  <strong style={styles.sourceCount}>
                    {count}
                  </strong>

                </div>

              )
            )}

          </div>

        </div>

      </section>


      {/* ================================================= */}
      {/* EVENTS */}
      {/* ================================================= */}

      <section style={styles.panel}>

        <h2 style={styles.panelTitle}>
          Transaction Event Volume
        </h2>

        <p style={styles.panelDescription}>
          decision_events 테이블에 실제로 기록된 이벤트 수
        </p>


        <div style={styles.eventGrid}>

          <EventCard
            label="SHOWN"
            value={data.event_counts.shown}
          />

          <EventCard
            label="SELECTED"
            value={data.event_counts.selected}
          />

          <EventCard
            label="HELD"
            value={data.event_counts.held}
          />

          <EventCard
            label="CONFIRMED"
            value={data.event_counts.confirmed}
          />

        </div>


        <div style={styles.explanationBox}>

          <strong>
            왜 SHOWN이 검색보다 많을 수 있나?
          </strong>

          <p style={styles.explanationText}>
            검색 1회에 후보 3개를 보여주면
            Patient Intent는 1개지만
            SHOWN DecisionEvent는 3개 생성됩니다.
          </p>

          <code style={styles.code}>
            Intent 1개 → Candidate 3개 → SHOWN 3개
          </code>

        </div>

      </section>


      {/* ================================================= */}
      {/* BUSINESS INTERPRETATION */}
      {/* ================================================= */}

      <section style={styles.panel}>

        <div style={styles.eyebrow}>
          WHY THIS MATTERS
        </div>

        <h2 style={styles.panelTitle}>
          검색 플랫폼에서 Decision Network로
        </h2>


        <div style={styles.networkFlow}>

          <FlowBox
            title="Intent"
            text="무엇을 원하는가"
          />

          <div style={styles.flowArrow}>
            →
          </div>

          <FlowBox
            title="Candidates"
            text="무엇을 보여줬는가"
          />

          <div style={styles.flowArrow}>
            →
          </div>

          <FlowBox
            title="Selection"
            text="무엇을 골랐는가"
          />

          <div style={styles.flowArrow}>
            →
          </div>

          <FlowBox
            title="Transaction"
            text="실제로 예약했는가"
          />

        </div>

      </section>


      <HospitalDecisionTable />


      <div style={styles.disclaimer}>
        현재 수치는 개발 및 테스트 과정에서 생성된
        합성 데이터입니다. 실제 사업 성과나 의료 품질을
        의미하지 않습니다.
      </div>

    </main>
  );
}


function KpiCard({
  label,
  value,
  description,
}: {
  label: string;
  value: number;
  description: string;
}) {

  return (
    <div style={styles.kpiCard}>

      <div style={styles.kpiLabel}>
        {label}
      </div>

      <div style={styles.kpiValue}>
        {value}
      </div>

      <div style={styles.kpiDescription}>
        {description}
      </div>

    </div>
  );
}


function MetricRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {

  return (
    <div style={styles.metricRow}>

      <span>
        {label}
      </span>

      <strong>
        {value}%
      </strong>

    </div>
  );
}


function EventCard({
  label,
  value,
}: {
  label: string;
  value: number;
}) {

  return (
    <div style={styles.eventCard}>

      <div style={styles.eventLabel}>
        {label}
      </div>

      <div style={styles.eventValue}>
        {value}
      </div>

    </div>
  );
}


function FlowBox({
  title,
  text,
}: {
  title: string;
  text: string;
}) {

  return (
    <div style={styles.flowBox}>

      <strong>
        {title}
      </strong>

      <span style={styles.flowText}>
        {text}
      </span>

    </div>
  );
}


const styles: Record<string, CSSProperties> = {

  page: {
    minHeight: "100vh",
    background: "#f6f7f9",
    color: "#111827",
    padding: "48px",
    fontFamily:
      "Arial, Helvetica, sans-serif",
  },

  header: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "24px",
    marginBottom: "32px",
    maxWidth: "1400px",
    marginLeft: "auto",
    marginRight: "auto",
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
    fontSize: "38px",
    letterSpacing: "-0.04em",
  },

  subtitle: {
    marginTop: "12px",
    color: "#64748b",
    fontSize: "15px",
  },

  liveBadge: {
    border: "1px solid #dbe2ea",
    borderRadius: "999px",
    background: "#ffffff",
    padding: "9px 13px",
    fontSize: "11px",
    fontWeight: 800,
    letterSpacing: "0.08em",
  },

  kpiGrid: {
    maxWidth: "1400px",
    margin: "0 auto 20px auto",
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(210px, 1fr))",
    gap: "16px",
  },

  kpiCard: {
    background: "#ffffff",
    border: "1px solid #e4e7ec",
    borderRadius: "16px",
    padding: "22px",
  },

  kpiLabel: {
    color: "#64748b",
    fontSize: "13px",
    fontWeight: 600,
  },

  kpiValue: {
    fontSize: "36px",
    fontWeight: 800,
    marginTop: "10px",
    letterSpacing: "-0.04em",
  },

  kpiDescription: {
    marginTop: "8px",
    color: "#94a3b8",
    fontSize: "12px",
  },

  panel: {
    maxWidth: "1400px",
    margin: "0 auto 20px auto",
    background: "#ffffff",
    border: "1px solid #e4e7ec",
    borderRadius: "16px",
    padding: "24px",
  },

  panelHeader: {
    display: "flex",
    justifyContent: "space-between",
  },

  panelTitle: {
    margin: 0,
    fontSize: "19px",
    letterSpacing: "-0.02em",
  },

  panelDescription: {
    marginTop: "7px",
    marginBottom: "20px",
    color: "#94a3b8",
    fontSize: "13px",
  },

  funnelList: {
    display: "flex",
    flexDirection: "column",
    gap: "13px",
  },

  funnelRow: {
    display: "grid",
    gridTemplateColumns: "150px 1fr",
    alignItems: "center",
    gap: "16px",
  },

  funnelLabel: {
    display: "flex",
    flexDirection: "column",
    gap: "3px",
  },

  funnelCode: {
    fontSize: "10px",
    color: "#94a3b8",
    fontFamily: "monospace",
  },

  barTrack: {
    width: "100%",
    minHeight: "42px",
    borderRadius: "10px",
    background: "#f1f5f9",
    overflow: "hidden",
  },

  barFill: {
    minHeight: "42px",
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    padding: "0 13px",
    boxSizing: "border-box",
    borderRadius: "10px",
    background: "#e2e8f0",
    transition: "width 0.25s ease",
  },

  twoColumn: {
    maxWidth: "1400px",
    margin: "0 auto",
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(320px, 1fr))",
    gap: "20px",
  },

  metricRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 0",
    borderBottom: "1px solid #f1f5f9",
    fontSize: "14px",
  },

  finalConversion: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: "18px",
    borderRadius: "12px",
    background: "#f8fafc",
    padding: "16px",
    fontWeight: 700,
  },

  finalRate: {
    fontSize: "22px",
  },

  sourceList: {
    display: "flex",
    flexDirection: "column",
  },

  sourceRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 0",
    borderBottom: "1px solid #f1f5f9",
  },

  sourceName: {
    fontSize: "13px",
    fontFamily: "monospace",
    fontWeight: 700,
  },

  sourceHint: {
    color: "#94a3b8",
    fontSize: "11px",
    marginTop: "4px",
  },

  sourceCount: {
    fontSize: "22px",
  },

  eventGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "12px",
  },

  eventCard: {
    background: "#f8fafc",
    borderRadius: "12px",
    padding: "18px",
  },

  eventLabel: {
    color: "#64748b",
    fontSize: "11px",
    fontFamily: "monospace",
  },

  eventValue: {
    marginTop: "8px",
    fontSize: "28px",
    fontWeight: 800,
  },

  explanationBox: {
    marginTop: "20px",
    padding: "18px",
    background: "#f8fafc",
    borderRadius: "12px",
    fontSize: "13px",
  },

  explanationText: {
    color: "#64748b",
    marginBottom: "10px",
  },

  code: {
    color: "#475569",
  },

  networkFlow: {
    marginTop: "22px",
    display: "flex",
    alignItems: "center",
    gap: "10px",
    flexWrap: "wrap",
  },

  flowBox: {
    minWidth: "150px",
    flex: 1,
    border: "1px solid #e4e7ec",
    borderRadius: "12px",
    padding: "18px",
    display: "flex",
    flexDirection: "column",
  },

  flowText: {
    marginTop: "7px",
    color: "#64748b",
    fontSize: "12px",
  },

  flowArrow: {
    color: "#94a3b8",
    fontSize: "20px",
  },

  disclaimer: {
    maxWidth: "1400px",
    margin: "12px auto 0 auto",
    paddingBottom: "30px",
    color: "#94a3b8",
    fontSize: "11px",
    textAlign: "center",
  },

  loadingCard: {
    maxWidth: "700px",
    margin: "100px auto",
    background: "#ffffff",
    border: "1px solid #e4e7ec",
    borderRadius: "16px",
    padding: "30px",
  },

  errorCard: {
    maxWidth: "700px",
    margin: "100px auto",
    background: "#ffffff",
    border: "1px solid #e4e7ec",
    borderRadius: "16px",
    padding: "30px",
  },

  errorTitle: {
    marginTop: 0,
  },

  muted: {
    color: "#64748b",
  },
};