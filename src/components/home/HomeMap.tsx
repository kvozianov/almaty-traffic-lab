"use client";

import { useEffect } from "react";
import Link from "next/link";
import { baselineFlow, baselineVc } from "@/lab/client/baseline";
import { useCityData } from "@/lab/client/data";
import { prewarmEngine } from "@/lab/client/useEngine";
import { formatInt } from "@/lab/format";
import LabMap from "@/components/lab/LabMap";
import styles from "./Home.module.css";

/** Static preview of the morning peak, computed by the same engine as the lab. */
export default function HomeMap() {
  const { data } = useCityData();
  // Compute today's baseline routes in the background while the visitor reads,
  // so the lab and the example questions open without a wait.
  useEffect(() => {
    if (!data) return;
    const id = window.setTimeout(prewarmEngine, 1200);
    return () => window.clearTimeout(id);
  }, [data]);
  return (
    <div className={styles.mapFrame}>
      {data ? (
        <LabMap
          data={data}
          interactive={false}
          coloring={{ kind: "load", flow: baselineFlow(data, "am"), vc: baselineVc(data, "am") }}
        />
      ) : (
        <div className={styles.mapPlaceholder} />
      )}
      <div className={styles.mapCaption}>
        <p className="label">Morning peak · today</p>
        <p className={styles.mapCaptionValue}>
          {data ? formatInt(Math.round(data.baseline.periods.am.metrics.trips / 1000) * 1000) : "275,000"} car trips
        </p>
        <p className="small">
          Average {data ? data.baseline.periods.am.metrics.avgSpeedKmh.toFixed(0) : "27"} km/h on main roads
        </p>
      </div>
      <Link href="/lab" className={`btn btn-primary ${styles.mapCta}`}>
        Open the lab →
      </Link>
    </div>
  );
}
