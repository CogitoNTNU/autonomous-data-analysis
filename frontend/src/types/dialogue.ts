import type {
  AnalysisFigure,
  AnalysisPlan,
  AnalysisReport,
  AnalysisTable,
  ChatAnswer,
  CritiqueView,
  InterpretationView,
  PreprocessingReport,
} from "@/types/planner";

export type DialogueTurn = {
  role: "user" | "assistant";
  content: string;
  analysisRound: number;
  referencedIds: string[];
  startsAnalysis: boolean;
  failed: boolean;
};

export type AnalysisRound = {
  round: number;
  answer: ChatAnswer;
  figures: AnalysisFigure[];
  tables: AnalysisTable[];
  plan: AnalysisPlan | null;
  report: PreprocessingReport | null;
  analysis: AnalysisReport | null;
  interpretation: InterpretationView | null;
  critique: CritiqueView | null;
};
