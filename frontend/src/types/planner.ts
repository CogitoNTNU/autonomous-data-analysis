export type ClarificationReason =
  | "ambiguous_objective"
  | "missing_information"
  | "missing_column"
  | "unsupported_request";

export type ClarificationOption = {
  id: string;
  label: string;
};

export type ClarificationRequest = {
  reason: ClarificationReason;
  question: string;
  description: string;
  options: ClarificationOption[];
};

export type PlanStep = {
  id: string;
  title: string;
  description: string;
};

export type StoredPlanStep = {
  step_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  depends_on: string[];
};

export type StoredPlan = {
  plan_id: string;
  objective: string;
  required_columns: string[];
  preprocessing_steps: StoredPlanStep[];
  analysis_steps: StoredPlanStep[];
  expected_outputs: string[];
  assumptions: string[];
};

export type AnalysisPlan = {
  id: string;
  objective: string;
  steps: PlanStep[];
  assumptions: string[];
  status: "draft";
  source: StoredPlan;
};

export type PreprocessingReport = {
  changes: string[];
  affectedColumns: string[];
  rowsBefore: number;
  rowsAfter: number;
  warnings: string[];
};

export type AnalysisStepView = {
  id: string;
  method: string;
  sampleSize: number;
  detail: string;
  warnings: string[];
};

export type AnalysisFigure = {
  id: string;
  image: string;
};

export type AnalysisTable = {
  id: string;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  groupSizes?: number[];
  sampleSize: number;
};

export type AnalysisReport = {
  steps: AnalysisStepView[];
  figures: AnalysisFigure[];
  tables?: AnalysisTable[];
  warnings: string[];
  results: Record<string, unknown>[];
  artifacts: { artifact_id: string; type: string }[];
};

export type FindingView = {
  claim: string;
  resultIds: string[];
};

export type InterpretationView = {
  summary: string;
  findings: FindingView[];
  limitations: string[];
  unanswered: string[];
  source: Record<string, unknown>;
};

export type CritiqueView = {
  decision: "approved" | "revise" | "cannot_complete";
  issues: string[];
  requiredChanges: string[];
  source: Record<string, unknown>;
};

export type ChatAnswer = {
  text: string;
  findings: FindingView[];
  limitations: string[];
  figureIds: string[];
  followUps: string[];
};
