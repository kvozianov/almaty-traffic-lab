export type ClaimLevel =
  | "demo"
  | "proxy"
  | "calibrated"
  | "real-data"
  | "procurement-ready";

export type ClaimInput = ClaimLevel | string | null | undefined;

export interface SourceRecord {
  id: string;
  label: string;
  path?: string;
  claim_label?: ClaimInput;
  claimLevel?: ClaimInput;
  source_type?: string;
  sourceType?: string;
  provider?: string;
  owner?: string;
  available?: boolean;
  legal_mode?: string;
  freshness?: string;
  last_refresh?: string | null;
  sha256?: string | null;
  bytes?: number | null;
  limitations?: string[];
  notes?: string;
}

export interface KpiRecord {
  id: string;
  label: string;
  unit: string;
  baseline: number;
  measure: number;
  delta: number;
  direction: "higher_is_better" | "lower_is_better" | string;
  claimLevel: ClaimInput;
  formula: string;
  placeholder: boolean;
  available: boolean;
}

export interface DossierJson {
  id: string;
  claimLevel: ClaimInput;
  corridor: {
    id: string;
    name: string;
    anchor?: string;
    lengthKm?: number;
    intersectionCount?: number;
  };
  proposedMeasure: {
    label: string;
    type: string;
    description: string;
    analyticsPath?: string;
    summary?: Record<string, number>;
  };
  decisionQuestion: string;
  recommendation: {
    decision: string;
    rationale: string;
    allowedDecisions: string[];
    claimLevel: ClaimInput;
  };
  baseline: {
    label: string;
    analyticsPath?: string;
    summary?: Record<string, number>;
  };
  executiveKpis: {
    claimLevel: ClaimInput;
    confidence?: {
      level: string;
      score: number;
      claimLevel: ClaimInput;
      notes: string;
    };
    assumptions?: Record<string, number>;
    kpis: KpiRecord[];
  };
  assumptions: string[];
  limitations: string[];
  risks: string[];
  sources: SourceRecord[];
  capexOpex?: {
    capexKzt: number;
    opexKztPerYear: number;
    claimLevel: ClaimInput;
    notes: string;
  };
  outputs: Record<string, string>;
  trustMetadata?: RunPassportJson;
  pairedExperiment?: Record<string, unknown>;
}

export interface RunPassportJson {
  runId: string;
  createdAt: string;
  model?: {
    name?: string;
    version?: string;
    gitHash?: string;
  };
  seed?: number;
  scenarioParams?: Record<string, unknown>;
  dataSources?: SourceRecord[];
  calibrationValidation?: {
    claimLabel?: ClaimInput;
    path?: string;
    available?: boolean;
    segmentCount?: number;
    intersectionCount?: number;
    observedVsSimulated?: unknown[];
    notes?: string;
  };
  limitations?: string[];
  claimLabels?: Record<string, ClaimInput>;
  audit?: Record<string, string>;
}

export interface ProviderRegistryJson {
  summary?: {
    providerCount?: number;
    availableCount?: number;
    realDataAvailableCount?: number;
    refreshableSource?: string;
  };
  providers: SourceRecord[];
}

export interface WorkflowHistoryItem {
  fromStatus: string | null;
  toStatus: string;
  owner: string;
  timestamp: string;
  evidencePath: string;
  evidenceSha256?: string;
  comments?: string;
  nextAction?: string;
  requiredEvidenceSatisfied?: boolean;
  claimLevel: ClaimInput;
  recalibrationRequired?: boolean;
}

export interface WorkflowJson {
  status: string;
  currentOwner: string;
  claimLevel: ClaimInput;
  evidenceCompleteness?: {
    historyCount?: number;
    satisfiedEvidenceCount?: number;
    allRequiredEvidencePresent?: boolean;
  };
  statusSequence: string[];
  artifactLocks: Array<{
    path: string;
    available: boolean;
    sha256?: string;
    bytes?: number;
  }>;
  history: WorkflowHistoryItem[];
  outputs: Record<string, string>;
  limitations: string[];
}

export interface ProcurementJson {
  claimLevel: ClaimInput;
  summary?: {
    requirementCount?: number;
    statuses?: Record<string, number>;
    claimLevels?: Record<string, number>;
    acceptanceGate?: string;
  };
  requirements: Array<{
    id: string;
    area: string;
    requirement: string;
    status: string;
    claim_level: ClaimInput;
    evidence: string[];
    gap: string;
    next_action: string;
  }>;
  limitations: string[];
  outputs: Record<string, string>;
  localOnPremRunPath?: string[];
}

export interface ReproMetadataJson {
  id: string;
  claimLevel: ClaimInput;
  seed?: number;
  configPath?: string;
  scenarioConfigPath?: string;
  sourceControl?: {
    gitHash?: string;
    dirty?: boolean;
    dirtyEntryCount?: number;
    note?: string;
  };
  inputFingerprints?: Array<{
    path: string;
    available: boolean;
    sha256?: string;
    bytes?: number;
  }>;
  commands?: Array<{
    role: string;
    command: string[];
    environment?: Record<string, string>;
    expectedPath?: string;
    stdout?: string;
  }>;
  outputs?: Record<string, unknown>;
  artifactCount?: number;
  reproducibilityNotes?: string[];
  claimLabels?: Record<string, ClaimInput>;
}

export interface ArtifactManifestJson {
  claimLevel: ClaimInput;
  artifacts: Array<{
    kind: string;
    path: string;
    claimLevel: ClaimInput;
    bytes?: number;
    sha256?: string;
  }>;
}

export interface PortfolioJson {
  title: string;
  claimLevel: ClaimInput;
  baseline?: {
    label?: string;
    analyticsPath?: string;
    summary?: Record<string, number>;
  };
  matrix: Array<{
    rank: number;
    scenario_id: string;
    scenario_name: string;
    scenario_type: string;
    claim_level: ClaimInput;
    decision_signal: string;
    person_hours_saved?: number;
    corridor_speed_delta?: number;
    bus_reliability_proxy?: number;
    capex_placeholder?: number;
    roi_proxy?: number;
    payback_proxy?: number;
  }>;
  outputs?: Record<string, string>;
  limitations?: string[];
}

export interface PackFileRecord {
  role: string;
  kind: string;
  path: string;
  claimLevel: ClaimInput;
  required?: boolean;
  available?: boolean;
  bytes?: number | null;
  sha256?: string | null;
}

export interface ProcurementPackIndexJson {
  id: string;
  kind: string;
  claimLevel: ClaimInput;
  createdAt: string;
  scenarioId: string;
  dossierClaimLevel: ClaimInput;
  currentSafePosition: string;
  decisionSummary?: {
    decision?: string;
    rationale?: string;
    allowedDecisions?: string[];
    claimLevel?: ClaimInput;
  };
  inputs: PackFileRecord[];
  outputs: PackFileRecord[];
  includedSections: string[];
  apiBoundary?: Record<string, string>;
  limitations: string[];
}

export interface ApplicationPackageIndexJson {
  id: string;
  kind: string;
  claimLevel: ClaimInput;
  createdAt: string;
  scenarioId: string;
  currentSafePosition: string;
  recommendedReviewSequence: string[];
  files: PackFileRecord[];
  nextAction: string;
}

export interface DataReadinessJson {
  id: string;
  claimLevel: ClaimInput;
  providerSummary?: Record<string, number | string | null>;
  akimatRequests?: Array<{
    id: string;
    dataset: string;
    requested_owner: string;
    why_needed: string;
    minimum_format: string;
    current_claim_level: ClaimInput;
    claim_upgrade_use: string;
  }>;
  missingEvidence?: Array<{
    id: string;
    dataset: string;
    currentClaimLevel: ClaimInput;
    blocks: string;
    status: string;
  }>;
}

export interface PilotMonitoringPlanJson {
  id: string;
  claimLevel: ClaimInput;
  baselineMeasurementWindow: string;
  pilotMeasurementWindow: string;
  criteria: Array<{
    id: string;
    kpi_id: string;
    owner: string;
    data_source: string;
    acceptable_threshold: string;
    recalibration_trigger: string;
    current_claim_level: ClaimInput;
  }>;
  decisionAfterPilot: string[];
}

export type PortfolioArtifactRole =
  | "dossier"
  | "runPassport"
  | "providers"
  | "workflow"
  | "procurement"
  | "reproduction"
  | "manifest"
  | "dataReadiness"
  | "procurementPack"
  | "applicationPack"
  | "pilotPlan";

export interface PortfolioRouteArtifact {
  role: PortfolioArtifactRole;
  runId: string;
  logicalPath: string;
  sha256: string;
  bytes: number;
  mediaType: string;
  claimLevel: ClaimLevel;
}

export type PortfolioDownloadId =
  | "dossier-html"
  | "dossier-json"
  | "kpis-csv"
  | "run-passport-json"
  | "procurement-index-json";

export interface PortfolioDownloadArtifact {
  id: PortfolioDownloadId;
  runId: string;
  logicalPath: string;
  sha256: string;
  bytes: number;
  mediaType: "text/html" | "application/json" | "text/csv";
  filename: string;
}

export interface PortfolioRouteManifest {
  schemaVersion: "portfolio-route-manifest/v1";
  runId: string;
  scenarioId: "abay-signal-retiming";
  claimLevel: ClaimLevel;
  generatedAt: string;
  status: "promoted";
  sourceManifest: {
    path: string;
    sha256: string;
  };
  artifacts: PortfolioRouteArtifact[];
  downloads: PortfolioDownloadArtifact[];
  aliases: {
    status: "pending" | "synced" | "failed";
    errors: string[];
    paths: Array<{
      role: PortfolioArtifactRole;
      path: string;
    }>;
  };
}
