import type { Metadata } from "next";

import AbayCorridorMap from "@/components/dossier/LazyAbayCorridorMap";
import AssumptionList from "@/components/dossier/AssumptionList";
import ClaimBadge from "@/components/dossier/ClaimBadge";
import DecisionActionBar from "@/components/dossier/DecisionActionBar";
import DownloadActions, { type DownloadArtifact } from "@/components/dossier/DownloadActions";
import EvidenceGate from "@/components/dossier/EvidenceGate";
import KpiDeltaTable from "@/components/dossier/KpiDeltaTable";
import ProcurementReadinessPanel from "@/components/dossier/ProcurementReadinessPanel";
import RunPassportCard from "@/components/dossier/RunPassportCard";
import { formatDecision, formatNumber } from "@/components/dossier/format";
import { isEmpiricalCalibrationComplete } from "@/components/dossier/evidence";
import { loadPromotedPortfolioRelease } from "@/components/dossier/portfolioRelease";
import { normalizeClaimLevel } from "@/components/dossier/ClaimBadge";
import type {
  ApplicationPackageIndexJson,
  ArtifactManifestJson,
  DataReadinessJson,
  DossierJson,
  KpiRecord,
  PilotMonitoringPlanJson,
  ProcurementJson,
  ProcurementPackIndexJson,
  ProviderRegistryJson,
  ReproMetadataJson,
  RunPassportJson,
  SourceRecord,
  WorkflowJson,
} from "@/components/dossier/types";
import styles from "./DossierPage.module.css";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Abay Avenue signal-retiming case",
  description: "A reproducible proxy case dossier for signal retiming on Abay Avenue.",
  alternates: {
    canonical: "/scenarios/abay-signal-retiming/dossier",
  },
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "Abay Avenue signal-retiming case",
    description: "A reproducible proxy case dossier for signal retiming on Abay Avenue.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Abay Avenue signal-retiming case",
    description: "A reproducible proxy case dossier for signal retiming on Abay Avenue.",
  },
};

type KpiRow = {
  label: string;
  before: string;
  after: string;
  delta: string;
  direction: "up" | "down" | "flat";
  tone: "positive" | "negative" | "neutral";
  claimLevel: KpiRecord["claimLevel"];
};

type EvidenceItem = {
  label: string;
  complete: boolean;
};

const HERO_KPI_IDS = [
  "person_hours_saved",
  "corridor_speed_delta",
  "bus_reliability_proxy",
  "co2_proxy",
];

const HERO_KPI_LABELS: Record<string, string> = {
  person_hours_saved: "Person-hours saved",
  corridor_speed_delta: "Corridor speed",
  bus_reliability_proxy: "Bus reliability",
  co2_proxy: "CO₂ emissions",
};

function hasValidDate(value?: string) {
  if (!value) return false;
  return !Number.isNaN(new Date(value).getTime());
}

function translateRecommendation(value: string) {
  const normalized = value.toLowerCase();

  if (normalized.includes("proxy benefit appears positive")) {
    return "The proxy result is favourable, but the evidence is insufficient for immediate funding.";
  }

  if (normalized.includes("primary proxy kpi directions are favorable")) {
    return "Primary proxy indicators are favourable, but the evidence level and cost estimate do not support a funding decision yet.";
  }

  return value;
}

function translateCostNote(value: string) {
  if (value.toLowerCase().includes("placeholder until supplied by akimat or engineering estimate")) {
    return "Placeholder pending a city or engineering cost estimate.";
  }

  return value;
}

function translateCorridorName(value: string) {
  if (value === "Abay Avenue") return "Abay Avenue";
  return value;
}

function translateUnit(unit: string) {
  const normalized = unit.toLowerCase();

  if (normalized.includes("person-hour")) return "person-hours";
  if (normalized === "km/h") return "km/h";
  if (normalized === "percentage points") return "pp";
  if (normalized === "kg") return "kg";

  return unit;
}

function translateWorkflowStatus(value: string) {
  if (value === "audited") return "audited";
  if (value === "draft") return "draft";
  return value;
}

function normalizeKpi(kpi: KpiRecord): KpiRecord {
  return {
    ...kpi,
    available: kpi.available ?? true,
  };
}

function formatHeroValue(value: number, unit: string) {
  const unitLabel = translateUnit(unit);

  if (unit.toLowerCase().includes("kzt")) {
    return `${new Intl.NumberFormat("en-GB", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)} ₸`;
  }

  return `${new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: Math.abs(value) >= 100 ? 0 : 2,
  }).format(value)} ${unitLabel}`;
}

function readSignalDelay(
  scenarioParams: Record<string, unknown> | undefined,
  key: "baseline" | "measure",
) {
  const candidate = scenarioParams?.[key];
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;

  const delay = (candidate as Record<string, unknown>).signal_delay_s;
  return typeof delay === "number" && Number.isFinite(delay) ? delay : null;
}

function formatSignalDelay(value: number | null) {
  return value === null ? "Not recorded" : `${formatNumber(value)} s`;
}

function buildHeroKpiRows(kpis: KpiRecord[]): KpiRow[] {
  return HERO_KPI_IDS.map((id) => kpis.find((kpi) => kpi.id === id))
    .filter((kpi): kpi is KpiRecord => Boolean(kpi))
    .map((kpi) => {
      const improved =
        kpi.delta === 0
          ? false
          : kpi.direction === "higher_is_better"
            ? kpi.delta > 0
            : kpi.delta < 0;

      return {
        label: HERO_KPI_LABELS[kpi.id] ?? kpi.label,
        before: formatHeroValue(kpi.baseline, kpi.unit),
        after: formatHeroValue(kpi.measure, kpi.unit),
        delta: `${kpi.delta > 0 ? "+" : ""}${formatHeroValue(kpi.delta, kpi.unit)}`,
        direction: kpi.delta === 0 ? "flat" : kpi.delta > 0 ? "up" : "down",
        tone: kpi.delta === 0 ? "neutral" : improved ? "positive" : "negative",
        claimLevel: kpi.claimLevel,
      };
    });
}

function DossierIntro({
  corridorName,
  lengthKm,
  intersectionCount,
  baselineDelay,
  measureDelay,
  rationale,
  claimLevel,
  currentDecision,
}: {
  corridorName: string;
  lengthKm?: number;
  intersectionCount?: number;
  baselineDelay: number | null;
  measureDelay: number | null;
  rationale: string;
  claimLevel: KpiRecord["claimLevel"];
  currentDecision: string;
}) {
  const corridorDetails = [
    corridorName,
    typeof lengthKm === "number" && Number.isFinite(lengthKm) ? `${lengthKm.toFixed(1)} km` : null,
    typeof intersectionCount === "number" && intersectionCount > 0
      ? `${intersectionCount} intersections`
      : null,
  ].filter(Boolean);

  return (
    <header className={styles.hero}>
      <div className={styles.heroMeta}>
        <span>Case 01</span>
        <span>{corridorDetails.join(" · ")}</span>
        <span>Controlled proxy comparison</span>
      </div>

      <div className={styles.heroGrid}>
        <div>
          <h1 className={styles.displayTitle}>{corridorName} signal-retiming case</h1>
          <div className={styles.controlledChange} aria-label={`Controlled change from ${formatSignalDelay(baselineDelay)} to ${formatSignalDelay(measureDelay)}`}>
            <span className={styles.changeLabel}>Controlled signal-delay change</span>
            <span className={styles.changeValue}>{formatSignalDelay(baselineDelay)}</span>
            <span className={styles.changeArrow} aria-hidden="true">→</span>
            <span className={styles.changeValue}>{formatSignalDelay(measureDelay)}</span>
          </div>
        </div>

        <aside className={styles.heroAside} aria-label="Evidence summary">
          <div className="flex flex-wrap items-center gap-2">
            <p className={styles.eyebrow}>Current recommendation</p>
            <ClaimBadge level={claimLevel} />
          </div>
          <p className={styles.recommendation}>{formatDecision(currentDecision)}</p>
          <p className={styles.rationale}>{rationale}</p>
          <div className={styles.actionRow} data-print-hidden>
            <a className={styles.primaryLink} href="#evidence">Review evidence</a>
            <a className={styles.secondaryLink} href="#downloads">Download dossier</a>
          </div>
        </aside>
      </div>
    </header>
  );
}

function KpiTable({ rows }: { rows: KpiRow[] }) {
  return (
    <section className={styles.ledger} aria-label="Core KPI comparison">
      <div className={styles.ledgerHeader} aria-hidden="true">
        <span>Metric</span>
        <span>Baseline → measure</span>
        <span>Change</span>
        <span className="text-right">Evidence</span>
      </div>
      <div>
        {rows.map((row) => (
          <div
            key={row.label}
            className={styles.ledgerRow}
          >
            <div className={styles.metricLabel}>{row.label}</div>
            <div className={styles.comparison}>
              <span className={styles.comparisonMuted}>{row.before}</span>
              <span className={styles.comparisonArrow}>→</span>
              <span>{row.after}</span>
            </div>
            <div
              className={`${styles.delta} ${
                row.tone === "positive"
                  ? styles.positive
                  : row.tone === "negative"
                    ? styles.negative
                    : styles.neutral
              }`}
            >
              <span>{row.delta}</span>
              {row.direction !== "flat" ? <span aria-hidden="true">{row.direction === "up" ? "↑" : "↓"}</span> : null}
            </div>
            <div className={styles.claimCell}>
              <ClaimBadge level={row.claimLevel} size="xs" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function EvidenceGateSummary({
  items,
}: {
  items: EvidenceItem[];
}) {
  const completed = items.filter((item) => item.complete).length;
  const total = items.length;

  return (
    <div className={styles.summaryCell}>
      <div className={styles.evidenceTopline}>
        <p className={styles.summaryTitle}>Evidence check</p>
        <p className={styles.evidenceCount}>{completed} / {total}</p>
      </div>
      <div className={styles.evidenceList}>
        {items.map((item, index) => (
          <div key={item.label} className={styles.evidenceItem}>
            <span className={styles.evidenceIndex} aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            <span>{item.label}</span>
            <span className={`${styles.evidenceState} ${item.complete ? styles.stateReady : styles.stateGap}`}>
              {item.complete ? "ready" : "gap"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionBar({
  currentDecision,
  allowedDecisions,
}: {
  currentDecision: string;
  allowedDecisions: string[];
}) {
  const hasCleanFund = allowedDecisions.includes("fund");

  return (
    <div className={styles.summaryCell}>
      <p className={styles.summaryTitle}>Decision gate</p>
      <div className={styles.decisionGrid} aria-label="Decision status summary">
        <div className={styles.decisionItem}>
          <p className={styles.microLabel}>Recommendation</p>
          <p className={styles.decisionValue}>{formatDecision(currentDecision)}</p>
        </div>
        <div className={styles.decisionItem}>
          <p className={styles.microLabel}>Unconditional funding</p>
          <p className={`${styles.decisionValue} ${hasCleanFund ? styles.positive : styles.negative}`}>
            {hasCleanFund ? "permitted by dossier" : "blocked"}
          </p>
        </div>
      </div>
    </div>
  );
}

function BottomStrip({
  evidenceItems,
  capexLabel,
  costNote,
  currentDecision,
  allowedDecisions,
}: {
  evidenceItems: EvidenceItem[];
  capexLabel: string;
  costNote: string;
  currentDecision: string;
  allowedDecisions: string[];
}) {
  return (
    <section className={styles.summaryStrip}>
      <div className={styles.summaryCell}>
        <p className={styles.summaryTitle}>Cost estimate</p>
        <p className={styles.summaryValue}>{capexLabel}</p>
        <p className={styles.summaryNote}>{costNote}</p>
      </div>
      <EvidenceGateSummary items={evidenceItems} />
      <DecisionBar currentDecision={currentDecision} allowedDecisions={allowedDecisions} />
    </section>
  );
}

function DataReadinessPanel({
  dataReadiness,
  providers,
  sources,
}: {
  dataReadiness: DataReadinessJson;
  providers: ProviderRegistryJson;
  sources: SourceRecord[];
}) {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <p className={styles.microLabel}>Data readiness</p>
          <h2 className={styles.panelTitle}>
            What to request from the city
          </h2>
        </div>
        <ClaimBadge level={dataReadiness.claimLevel} />
      </div>

      <div className={styles.statGrid}>
        <div className={styles.statCell}>
          <p className={styles.statLabel}>Sources</p>
          <p className={styles.statValue}>{providers.summary?.providerCount ?? providers.providers.length}</p>
        </div>
        <div className={styles.statCell}>
          <p className={styles.statLabel}>Available</p>
          <p className={styles.statValue}>{providers.summary?.availableCount ?? 0}</p>
        </div>
        <div className={styles.statCell}>
          <p className={styles.statLabel}>Missing</p>
          <p className={styles.statValue}>{dataReadiness.missingEvidence?.length ?? 0}</p>
        </div>
      </div>

      <div className={styles.subsection}>
        <p className={styles.microLabel}>Requested data sets</p>
        <div className={styles.rows}>
          {dataReadiness.akimatRequests?.map((request) => (
            <div key={request.id} className={styles.row}>
              <div className={styles.rowTopline}>
                <p className={styles.rowTitle}>{request.dataset}</p>
                <ClaimBadge level={request.current_claim_level} size="xs" />
              </div>
              <p className={styles.rowDescription}>{request.why_needed}</p>
              <p className={styles.monoPath}>{request.minimum_format}</p>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.subsection}>
        <p className={styles.microLabel}>Dossier sources</p>
        <div className={styles.rows}>
          {sources.map((source) => (
            <div key={source.id} className={styles.row}>
              <div className={styles.rowTopline}>
                <p className={styles.rowTitle}>{source.label}</p>
                <ClaimBadge level={source.claim_label ?? source.claimLevel} size="xs" />
              </div>
              <p className={styles.monoPath}>{source.path ?? source.provider ?? source.source_type}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function WorkflowCustodyPanel({ workflow }: { workflow: WorkflowJson }) {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <p className={styles.microLabel}>Verification chain · demo workflow</p>
          <h2 className={styles.panelTitle}>Recorded state: {translateWorkflowStatus(workflow.status)}</h2>
          <p className={styles.panelNote}>Current record owner: {workflow.currentOwner}. This is workflow custody, not independent assurance.</p>
        </div>
        <ClaimBadge level={workflow.claimLevel} />
      </div>

      <div className={styles.statGrid}>
        <div className={styles.statCell}>
          <p className={styles.statLabel}>History</p>
          <p className={styles.statValue}>{workflow.history.length}</p>
        </div>
        <div className={styles.statCell}>
          <p className={styles.statLabel}>Snapshots</p>
          <p className={styles.statValue}>{workflow.artifactLocks.length}</p>
        </div>
        <div className={styles.statCell}>
          <p className={styles.statLabel}>Evidence links</p>
          <p className={styles.statValue}>
            {workflow.evidenceCompleteness?.satisfiedEvidenceCount ?? 0}
          </p>
        </div>
      </div>

      <div className={styles.subsection}>
        <p className={styles.microLabel}>Artifact snapshots</p>
        <div className={styles.rows}>
          {workflow.artifactLocks.map((lock) => (
            <div key={lock.path} className={styles.row}>
              <div className={styles.rowTopline}>
                <p className={styles.monoPath}>{lock.path}</p>
                <span className={`${styles.availability} ${lock.available ? styles.available : styles.unavailable}`}>
                  {lock.available ? "available" : "unavailable"}
                </span>
              </div>
              {lock.sha256 ? <p className={styles.monoPath}>sha256 {lock.sha256}</p> : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ExportPackPanel({
  dossier,
  procurementPack,
  applicationPack,
  pilotPlan,
}: {
  dossier: DossierJson;
  procurementPack: ProcurementPackIndexJson;
  applicationPack: ApplicationPackageIndexJson;
  pilotPlan: PilotMonitoringPlanJson;
}) {
  const dossierOutputCount = Object.keys(dossier.outputs ?? {}).length;
  const packOutputCount = procurementPack.outputs.length;

  return (
    <section className={styles.exportSection}>
      <div className={styles.exportHeader}>
        <div>
          <p className={styles.microLabel}>Evidence pack context</p>
          <h2 className={styles.panelTitle}>Current release materials</h2>
        </div>
        <div className={styles.badgeGroup}>
          <ClaimBadge level={procurementPack.claimLevel} />
          <ClaimBadge level={dossier.claimLevel} />
        </div>
      </div>

      <div className={styles.exportGrid}>
        <div className={styles.exportItem}>
          <p className={styles.microLabel}>Dossier files</p>
          <p className={styles.exportValue}>{dossierOutputCount}</p>
          <p className={styles.exportCopy}>
            Read-only dossier formats are available through the download actions above.
          </p>
        </div>

        <div className={styles.exportItem}>
          <p className={styles.microLabel}>City review pack</p>
          <p className={styles.exportValue}>{packOutputCount}</p>
          <p className={styles.exportCopy}>
            These materials remain claim-labelled and do not make the dossier procurement-ready.
          </p>
        </div>

        <div className={styles.exportItem}>
          <p className={styles.microLabel}>How pilot success is assessed</p>
          <h3 className={styles.panelTitle}>{applicationPack.nextAction}</h3>
          <div className={styles.criteriaList}>
            {pilotPlan.criteria.map((criterion) => (
              <p key={criterion.id} className={styles.criterion}>
                {criterion.kpi_id}: {criterion.acceptable_threshold}
              </p>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export default async function AbaySignalRetimingDossierPage() {
  const release = await loadPromotedPortfolioRelease();
  const roadsSource = release.sources.roadsGeojson;
  if (!roadsSource) {
    throw new Error("The promoted release is missing its immutable roadsGeojson source.");
  }
  const dossier = release.artifacts.dossier as DossierJson;
  const runPassport = release.artifacts.runPassport as RunPassportJson;
  const providers = release.artifacts.providers as ProviderRegistryJson;
  const workflow = release.artifacts.workflow as WorkflowJson;
  const procurement = release.artifacts.procurement as ProcurementJson;
  const reproduction = release.artifacts.reproduction as ReproMetadataJson;
  const manifest = release.artifacts.manifest as ArtifactManifestJson;
  const dataReadiness = release.artifacts.dataReadiness as DataReadinessJson;
  const procurementPack = release.artifacts.procurementPack as ProcurementPackIndexJson;
  const applicationPack = release.artifacts.applicationPack as ApplicationPackageIndexJson;
  const pilotPlan = release.artifacts.pilotPlan as PilotMonitoringPlanJson;

  const normalizedKpis = dossier.executiveKpis.kpis.map(normalizeKpi);
  const heroKpiRows = buildHeroKpiRows(normalizedKpis);
  const corridorName = translateCorridorName(dossier.corridor?.name ?? "Abay Avenue");
  const lengthKm = dossier.corridor.lengthKm;
  const intersectionCount =
    dossier.corridor.intersectionCount ?? runPassport.calibrationValidation?.intersectionCount;
  const baselineDelay = readSignalDelay(runPassport.scenarioParams, "baseline");
  const measureDelay = readSignalDelay(runPassport.scenarioParams, "measure");
  const capexLabel = dossier.capexOpex ? formatNumber(dossier.capexOpex.capexKzt, "KZT") : "Not provided";
  const roadsProvider = providers.providers.find((provider) => provider.id === "roads-geojson");
  const scenarioConfigSource = dossier.sources.find((source) =>
    `${source.id} ${source.path ?? ""}`.toLowerCase().includes("scenario"),
  );
  const observedDataAvailable = providers.providers.some(
    (provider) =>
      provider.id !== "roads-geojson" &&
      provider.available === true &&
      normalizeClaimLevel(provider.claim_label ?? provider.claimLevel) === "real-data",
  );
  const costKpis = normalizedKpis.filter((kpi) =>
    ["capex_placeholder", "opex_placeholder"].includes(kpi.id),
  );
  const evidenceItems: EvidenceItem[] = [
    { label: "road geometry", complete: roadsProvider?.available === true },
    { label: "scenario configuration", complete: Boolean(scenarioConfigSource) },
    { label: "run passport", complete: Boolean(runPassport.runId) },
    { label: "calculation date", complete: hasValidDate(runPassport.createdAt) },
    { label: "observed data", complete: observedDataAvailable },
    {
      label: "empirical validation",
      complete: isEmpiricalCalibrationComplete(runPassport.calibrationValidation),
    },
    {
      label: "cost estimate",
      complete: costKpis.length === 2 && costKpis.every((kpi) => kpi.available && !kpi.placeholder),
    },
  ];
  const downloadLabels = {
    "dossier-html": "Download HTML dossier",
    "dossier-json": "Download JSON evidence",
    "kpis-csv": "Download KPI CSV",
    "run-passport-json": "Download run passport",
    "procurement-index-json": "Download procurement index",
  } as const;
  const downloadArtifacts: DownloadArtifact[] = release.manifest.downloads.map((artifact) => ({
    id: artifact.id,
    label: downloadLabels[artifact.id],
    logicalPath: artifact.logicalPath,
    sha256: artifact.sha256,
    bytes: artifact.bytes,
  }));
  const structuredProjectMetadata = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: "Abay Avenue signal-retiming case",
    description: "A reproducible proxy evidence dossier for signal retiming on Abay Avenue, Almaty.",
    about: {
      "@type": "Thing",
      name: "Signal retiming on Abay Avenue, Almaty",
    },
    isAccessibleForFree: true,
    inLanguage: "en",
    keywords: ["Almaty", "transport analysis", "signal retiming", "proxy evidence"],
  }).replace(/</g, "\\u003c");

  return (
    <main id="main-content" tabIndex={-1} className={styles.page}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: structuredProjectMetadata }} />

      <section className={styles.heroSection}>
        <div className={styles.inner}>
          <DossierIntro
            corridorName={corridorName}
            lengthKm={lengthKm}
            intersectionCount={intersectionCount}
            baselineDelay={baselineDelay}
            measureDelay={measureDelay}
            rationale={translateRecommendation(dossier.recommendation.rationale)}
            claimLevel={dossier.claimLevel}
            currentDecision={dossier.recommendation.decision}
          />
        </div>
      </section>

      <section id="result" className={`${styles.chapter} ${styles.chapterSurface}`}>
        <div className={styles.inner}>
          <header className={styles.chapterHeader}>
            <div>
              <p className={styles.eyebrow}>01 · Result</p>
              <h2 className={styles.chapterHeading}>A small modeled improvement.</h2>
            </div>
            <p className={styles.chapterDescription}>
              The controlled proxy comparison moves the selected indicators in a favourable direction,
              but observed traffic, empirical validation, and confirmed cost evidence remain incomplete.
            </p>
          </header>

          <div className={styles.resultGrid}>
            <div className={styles.resultLedger}>
              <KpiTable rows={heroKpiRows} />
              <BottomStrip
                evidenceItems={evidenceItems}
                capexLabel={capexLabel}
                costNote={
                  dossier.capexOpex
                    ? translateCostNote(dossier.capexOpex.notes)
                    : "No estimate source is recorded in the dossier."
                }
                currentDecision={dossier.recommendation.decision}
                allowedDecisions={dossier.recommendation.allowedDecisions}
              />
            </div>

            <figure className={styles.mapFigure}>
              <div className={styles.mapFrame}>
                <AbayCorridorMap
                  runId={release.manifest.runId}
                  expectedSourceSha256={roadsSource.sha256}
                  evidence={{
                    available: roadsProvider?.available === true,
                    claimLevel: normalizeClaimLevel(roadsProvider?.claim_label ?? roadsProvider?.claimLevel),
                    freshness: roadsProvider?.freshness,
                  }}
                />
              </div>
              <figcaption className={styles.mapCaption}>
                <span>Supporting exhibit · source-bound Abay corridor geometry</span>
                <span>non-live real-data snapshot</span>
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      <section id="methods" className={`${styles.chapter} ${styles.workbench}`}>
        <div className={styles.inner}>
          <header className={styles.workbenchIntro}>
            <div>
              <p className={styles.eyebrow}>02 · Evidence</p>
              <h2 className={styles.workbenchHeading}>Decision workbench</h2>
              <p className={styles.workbenchDescription}>
                Review the full evidence chain behind the summary: KPI JSON, run passport, source
                limitations, workflow custody, procurement gaps, and immutable export paths.
                {dossier.recommendation.allowedDecisions.includes("fund")
                  ? " Any funding decision still requires a separately recorded approval."
                  : " Unconditional funding is not available at the current evidence level."}
              </p>
            </div>
            <div className={styles.badgeGroup}>
              <span className={styles.releaseBadge} title={`Release ${release.manifest.runId}`}>
                immutable release · aliases {release.manifest.aliases.status}
              </span>
              <ClaimBadge level={dossier.claimLevel} />
              <ClaimBadge level={workflow.claimLevel} />
              <ClaimBadge level={procurement.claimLevel} />
            </div>
          </header>

          <div id="evidence" className={styles.workbenchStack}>
            <div className={styles.twoColumnWide}>
              <EvidenceGate
                currentClaimLevel={dossier.claimLevel}
                allowedDecisions={dossier.recommendation.allowedDecisions}
                risks={dossier.risks}
                limitations={dossier.limitations}
              />
              <RunPassportCard runPassport={runPassport} reproduction={reproduction} manifest={manifest} />
            </div>

            <KpiDeltaTable kpis={normalizedKpis} />

            <div className={styles.twoColumn}>
              <AssumptionList
                title="Assumptions, limitations, and risks"
                description="These are why the dossier remains a proxy-level decision file."
                items={[...dossier.assumptions, ...dossier.limitations, ...dossier.risks]}
                claimLevel={dossier.claimLevel}
              />
              <DataReadinessPanel
                dataReadiness={dataReadiness}
                providers={providers}
                sources={dossier.sources}
              />
            </div>

            <div className={styles.twoColumnWide}>
              <WorkflowCustodyPanel workflow={workflow} />
              <ProcurementReadinessPanel
                procurement={procurement}
                workflow={workflow}
                reproduction={reproduction}
                manifest={manifest}
              />
            </div>

            <div id="downloads">
              <DownloadActions
                artifacts={downloadArtifacts}
                runId={release.manifest.runId}
                releaseGeneratedAt={release.manifest.generatedAt}
                sourceManifestSha256={release.manifest.sourceManifest.sha256}
              />
            </div>

            <ExportPackPanel
              dossier={dossier}
              procurementPack={procurementPack}
              applicationPack={applicationPack}
              pilotPlan={pilotPlan}
            />
          </div>
        </div>
      </section>

      <DecisionActionBar
        currentDecision={dossier.recommendation.decision}
        allowedDecisions={dossier.recommendation.allowedDecisions}
        claimLevel={dossier.claimLevel}
      />
    </main>
  );
}
