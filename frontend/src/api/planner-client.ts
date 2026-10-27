import type { AnalysisResult } from "@/api/analysis-response";
import type { AnswerResult } from "@/api/answer-response";
import type { CritiqueResult } from "@/api/critique-response";
import type { InterpretationResult } from "@/api/interpretation-response";
import type { PreprocessResult } from "@/api/preprocessing-response";
import type {
  AnalysisPlan,
  AnalysisReport,
  ClarificationRequest,
  CritiqueView,
  InterpretationView,
  StoredPlan,
} from "@/types/planner";

export type PlannerMessage = {
  role: "user" | "assistant";
  content: string;
};

export type PlannerAsk = {
  datasetId: string;
  question: string;
  messages: PlannerMessage[];
  columns: string[];
  csv?: string;
};

export type PlannerResult =
  | { status: "plan"; plan: AnalysisPlan }
  | { status: "clarification"; clarification: ClarificationRequest }
  | { status: "error"; message: string };

export type PreprocessAsk = {
  datasetId: string;
  csv: string;
  plan: StoredPlan;
};

export type AnalysisAsk = PreprocessAsk;

export type InterpretationAsk = PreprocessAsk & {
  question: string;
  results: AnalysisReport["results"];
  artifacts: AnalysisReport["artifacts"];
};

export type CritiqueAsk = InterpretationAsk & {
  interpretation: InterpretationView;
};

export type AnswerAsk = {
  interpretation: InterpretationView;
  critique: CritiqueView;
};

export type PlannerClient = {
  registerDataset: (file: File) => Promise<{ dataset_id: string }>;
  ask: (input: PlannerAsk) => Promise<PlannerResult>;
  preprocess: (input: PreprocessAsk) => Promise<PreprocessResult>;
  analyze: (input: AnalysisAsk) => Promise<AnalysisResult>;
  interpret: (input: InterpretationAsk) => Promise<InterpretationResult>;
  critique: (input: CritiqueAsk) => Promise<CritiqueResult>;
  present: (input: AnswerAsk) => Promise<AnswerResult>;
};
