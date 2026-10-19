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

export type AnalysisPlan = {
  id: string;
  objective: string;
  steps: PlanStep[];
  assumptions: string[];
  status: "draft";
};
