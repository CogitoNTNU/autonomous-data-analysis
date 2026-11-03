import type { AnalysisFigure, AnalysisTable, ChatAnswer } from "@/types/planner";

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
};
