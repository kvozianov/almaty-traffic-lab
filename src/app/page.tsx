import Link from "next/link";
import HomeMap from "@/components/home/HomeMap";
import styles from "@/components/home/Home.module.css";
import { TRUST_ITEMS } from "@/components/lab/TrustNote";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";
import { EXAMPLES } from "@/lab/examples";
import { formatInt, PERIOD_LABELS } from "@/lab/format";
import calibration from "../../public/model/calibration.json";

const tripsAm = formatInt(Math.round(calibration.totalTrips / 1000) * 1000);
const tripsPm = formatInt(Math.round((calibration.totalTrips * calibration.periodFactors.pm) / 1000) * 1000);

const HOW = [
  {
    title: "Real streets",
    text: "3,500 junctions, 6,900 one-way road links and 665 traffic signals from OpenStreetMap, with lanes and speed limits.",
  },
  {
    title: "Real rush hours",
    text: `Traffic volumes by time of day are fitted to published Almaty data: Sergek ITS speed measurements, Yandex Traffic’s hourly profile and the city’s 2023 transport master plan. The evening peak carries ${tripsPm} car trips.`,
  },
  {
    title: "Every driver takes the fastest route",
    text: "Trips are routed again and again until nobody can save time by switching: user equilibrium, the standard planning model, solved in your browser in about a second.",
  },
];

const LEVEL = { real: "Real data", fitted: "Fitted to real data", standard: "Standard values", estimate: "Estimated" };

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <section className={`page ${styles.hero}`}>
          <p className="label">Almaty · a traffic model in your browser</p>
          <h1 className={`display ${styles.heroTitle}`}>What happens to Almaty traffic if…</h1>
          <p className={`lead ${styles.heroLead}`}>
            Close a street, give a lane to buses, retime the signals or build a housing estate. Then watch{" "}
            {tripsAm} morning car trips find new routes across the city’s real road network, with rush hours
            calibrated to measured Almaty traffic.
          </p>
          <div className={styles.heroActions}>
            <Link className="btn btn-primary" href="/lab">
              Open the lab
            </Link>
            <Link className="btn btn-secondary" href="/methods">
              How it works
            </Link>
          </div>
        </section>

        <section className="page" aria-label="Map preview">
          <HomeMap />
        </section>

        <section className={`page ${styles.section}`}>
          <div className={styles.sectionHead}>
            <p className="label">01</p>
            <h2 className="title">Start from a question</h2>
          </div>
          <ol className={styles.examples}>
            {EXAMPLES.map((ex, i) => (
              <li key={ex.id}>
                <Link href={`/lab?example=${ex.id}`}>
                  <span className="label">{String(i + 1).padStart(2, "0")}</span>
                  <span className={styles.exampleText}>
                    <span className={styles.exampleTitle}>{ex.title}</span>
                    <span className="small">{ex.question}</span>
                  </span>
                  <span className={`label ${styles.examplePeriod}`}>{PERIOD_LABELS[ex.period].long}</span>
                  <span aria-hidden="true" className={styles.arrow}>
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </section>

        <section className={`page ${styles.section}`}>
          <div className={styles.sectionHead}>
            <p className="label">02</p>
            <h2 className="title">How it works</h2>
          </div>
          <div className={styles.how}>
            {HOW.map((h) => (
              <div key={h.title}>
                <h3 className={styles.howTitle}>{h.title}</h3>
                <p className="body">{h.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={`page ${styles.section}`}>
          <div className={styles.sectionHead}>
            <p className="label">03</p>
            <h2 className="title">What is real, what is fitted, what is estimated</h2>
          </div>
          <dl className={styles.trust}>
            {TRUST_ITEMS.map((t) => (
              <div key={t.title}>
                <dt>
                  <span className={styles.trustTitle}>{t.title}</span>
                  <span className={`label ${styles[`level_${t.level}`]}`}>{LEVEL[t.level]}</span>
                </dt>
                <dd className="body">{t.text}</dd>
              </div>
            ))}
          </dl>
          <p className={`small ${styles.trustNote}`}>
            The lab is built to compare scenarios, not to forecast exact travel times. Trust the direction and the
            relative size of a change more than the precise number. <Link href="/methods">Read the method →</Link>
          </p>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
