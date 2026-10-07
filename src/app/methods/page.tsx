import type { Metadata } from "next";
import Link from "next/link";
import styles from "./Methods.module.css";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader, { REPO_URL } from "@/components/site/SiteHeader";
import { DEVELOPMENT_RATES } from "@/lab/engine/demand";
import { DEVELOPMENT_LABELS } from "@/lab/format";
import RealityCheck, { type CalibrationReport } from "@/components/methods/RealityCheck";
import type { Observations } from "@/lab/engine/observed";
import calibration from "../../../public/model/calibration.json";
import demandFile from "../../../public/model/demand.json";
import observationsFile from "../../../public/model/observations.json";

const observations = observationsFile as unknown as Observations;
const demand = demandFile as unknown as { zones: unknown[] };

export const metadata: Metadata = {
  title: "How it works",
  description: "The data, the traffic-assignment model and the limits of Almaty Traffic Lab.",
};

const CHANGES = [
  [
    "Close for repairs",
    "The section stops working as a main road in both directions. Drivers with no other main-road option squeeze through side streets, modelled as a detour at 10 km/h with room for about 2,500 cars an hour, which fills up like any road.",
  ],
  ["Give a lane to buses", "One lane fewer for cars in each direction (only where there are at least two)."],
  ["Widen by one lane", "One more lane in each direction, so capacity grows by one lane’s worth."],
  [
    "More green at signals",
    "Green share on the section’s approaches goes from 50% to 60%; crossing approaches at the same junctions drop to 40%.",
  ],
  ["Lower the speed limit to 40", "Free-flow speed on the section is capped at 40 km/h (× 0.85 for city driving)."],
  ["New building", "Adds car trips to and from the chosen point. Where they go follows the nearest zone’s pattern."],
];

export default function MethodsPage() {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className={`page ${styles.page}`}>
        <header className={styles.header}>
          <p className="label">How it works</p>
          <h1 className={`display ${styles.title}`}>A city-scale traffic model, small enough for a browser</h1>
          <p className="lead">
            The lab answers “what if” questions the way transport planners do: by finding where drivers would go
            if every one of them took the fastest route. This page explains what goes in, what the model does, and
            what it cannot tell you.
          </p>
        </header>

        <section className={styles.section}>
          <p className="label">01</p>
          <div>
            <h2 className="title">The road network</h2>
            <p className="body">
              Main roads of Almaty (motorway, trunk, primary, secondary and tertiary classes) come from an
              OpenStreetMap snapshot taken on 27 April 2026. Ways are split at junctions and traffic signals,
              chains without junctions are merged, and only the largest strongly connected part of the network is
              kept, so every junction can reach every other one.
            </p>
            <ul className={styles.facts}>
              <li>
                <span className="num">3,505</span> junctions
              </li>
              <li>
                <span className="num">6,871</span> one-way road links
              </li>
              <li>
                <span className="num">665</span> traffic signals
              </li>
              <li>
                <span className="num">932</span> street sections you can change
              </li>
            </ul>
            <p className="body">
              Each link gets lanes and a speed limit from OpenStreetMap (or a default for its road class) and a
              capacity of 1,200–1,900 cars per lane per hour depending on the class. At a signal, cars get green
              half of a 90-second cycle, so the approach carries half the lanes’ capacity; an empty junction costs
              about 11 seconds, and the wait grows as a queue builds.
            </p>
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">02</p>
          <div>
            <h2 className="title">Who drives where</h2>
            <p className="body">
              Almaty has no public survey of where every trip starts and ends, so demand is estimated, but pinned to
              the city’s own figures. The city is divided into {demand.zones.length} zones on a 2 km grid. Homes follow
              the length of residential streets and jobs the length of all streets, rescaled so that, as the 2023
              transport master plan states, {Math.round(observations.structure.jobsInCentreShare * 100)}% of jobs are in
              the centre (Raiymbek to Al-Farabi, Sain to Dostyk) and{" "}
              {Math.round(observations.structure.residentsOutsideCentreShare * 100)}% of residents live outside it. A
              gravity model then sends more trips to attractive zones that are close:
            </p>
            <pre className={styles.formula}>{`trips(i → j) = homes(i) × jobs(j) × e^(−β × minutes(i → j)) / Σk jobs(k) × e^(−β × minutes(i → k))`}</pre>
            <p className="body">
              How many cars there are at each time of day, and how far people drive (β), are not guessed: they are
              fitted to published measurements of Almaty traffic, shown in section 03.
            </p>
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">03</p>
          <div>
            <h2 className="title">Checked against real Almaty traffic</h2>
            <p className="body">
              No open dataset gives hourly traffic for every Almaty street: Yandex, 2GIS, TomTom and the city’s Sergek
              cameras keep theirs. What is public are individual measurements. The model is fitted to the ones below
              and then checked against a list it never saw.
            </p>
            <RealityCheck obs={observations} report={calibration as unknown as CalibrationReport} />
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">04</p>
          <div>
            <h2 className="title">Every driver takes the fastest route</h2>
            <p className="body">
              Travel time on a link grows with traffic. Between junctions it follows the standard Bureau of Public
              Roads curve; at a traffic signal it adds the Highway Capacity Manual control delay, whose queue term
              grows quickly once demand nears the green-time capacity. That is why signalised streets such as Abay
              jam long before an expressway such as Al-Farabi does.
            </p>
            <pre className={styles.formula}>{`link time   = free-flow time × (1 + 0.15 × (cars / capacity)⁴)
signal wait = ½ · cycle · (1 − g)² / (1 − min(1, x) · g)  +  15 · T · [(x − 1) + √((x − 1)² + 4x / (c · T))]
              x = cars / (capacity × g),  g = 0.5,  cycle = 90 s,  T = 0.25 h   (minutes)`}</pre>
            <p className="body">
              Drivers re-route until no one can arrive sooner by switching routes: Wardrop’s user equilibrium.
              The lab solves it with path-based gradient projection: each origin–destination pair keeps the routes
              it uses and shifts trips from slower to faster ones. A scenario starts from today’s routes, so only
              the trips your change affects have to move, which is why results arrive in about a second.
            </p>
            <p className="body">
              The solver stops when the remaining gap is below 0.05% of total travel time. A conjugate
              Frank–Wolfe solver, written independently, is used in the tests to confirm both reach the same
              equilibrium.
            </p>
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">05</p>
          <div>
            <h2 className="title">What each change does</h2>
            <dl className={styles.table}>
              {CHANGES.map(([title, text]) => (
                <div key={title}>
                  <dt>{title}</dt>
                  <dd className="body">{text}</dd>
                </div>
              ))}
            </dl>
            <p className="small" style={{ marginTop: 16 }}>
              New buildings, car trips in the morning peak hour:{" "}
              {(Object.keys(DEVELOPMENT_RATES) as (keyof typeof DEVELOPMENT_RATES)[])
                .map((k) => `${DEVELOPMENT_LABELS[k].title.toLowerCase()} ${DEVELOPMENT_RATES[k].perUnit.am} per ${DEVELOPMENT_RATES[k].unit.replace(/s$/, "").replace("m² of shops", "m²")}`)
                .join(" · ")}
              .
            </p>
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">06</p>
          <div>
            <h2 className="title">What the results mean</h2>
            <dl className={styles.table}>
              <div>
                <dt>Average trip on main roads</dt>
                <dd className="body">Minutes each car spends on the modelled network, averaged over all trips.</dd>
              </div>
              <div>
                <dt>Time spent driving</dt>
                <dd className="body">Vehicle-hours of all cars during the hour: the total cost of the traffic.</dd>
              </div>
              <div>
                <dt>Congested roads</dt>
                <dd className="body">Kilometres of one-way links where demand is above 90% of capacity.</dd>
              </div>
              <div>
                <dt>Moving dots on the map</dt>
                <dd className="body">
                  Each dot stands for a group of cars. More dots mean more vehicle-km on that road; dots move at the
                  modelled congested speed, with one second of animation showing 1.5 minutes of traffic.
                </dd>
              </div>
              <div>
                <dt>CO₂ from traffic</dt>
                <dd className="body">
                  Vehicle-km × a speed-dependent emission rate (about 165 g/km at 50 km/h, 340 g/km at 10 km/h). A
                  proxy for comparison, not an inventory.
                </dd>
              </div>
            </dl>
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">07</p>
          <div>
            <h2 className="title">Limits</h2>
            <ul className={styles.limits}>
              <li>Demand is estimated, not surveyed; it is fitted to a handful of published measurements, not to traffic counts on every street.</li>
              <li>Only cars on main roads are modelled. Buses, residential streets and parking are not.</li>
              <li>A static model: it describes an average peak hour, not queues building up and clearing minute by minute.</li>
              <li>People do not change when or whether they travel; they only change routes.</li>
              <li>Because of all this, compare scenarios with each other. Do not read the numbers as forecasts.</li>
            </ul>
          </div>
        </section>

        <section className={styles.section}>
          <p className="label">08</p>
          <div>
            <h2 className="title">Reproducible by design</h2>
            <p className="body">
              Road graph and demand are rebuilt byte-for-byte from the committed OpenStreetMap snapshot by Python
              scripts; their SHA-256 hashes are listed in a manifest. The engine is deterministic and avoids
              floating-point functions that differ between browsers, so a shared link reproduces the same result and
              the same run fingerprint anywhere. Automated tests cover the data build, the solver, every type of
              change and the URL format.
            </p>
            <p className="body">
              <a href={REPO_URL}>Source code on GitHub</a> · <Link href="/lab">Open the lab</Link>
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
