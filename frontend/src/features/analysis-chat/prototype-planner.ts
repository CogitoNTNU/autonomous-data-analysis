import type { PlannerClient } from "@/api/planner";
import type {
  AnalysisReport,
  ChatAnswer,
  CritiqueView,
  InterpretationView,
  PreprocessingReport,
} from "@/types/planner";

import { getPrototypeClarification } from "@/features/analysis-chat/prototype-clarification";
import { createPrototypeAnalysisPlan } from "@/features/analysis-chat/prototype-plan";

const PREVIEW_DELAY_MS = 500;
const CHAIN_DELAY_MS = 20;

export const prototypePlanner: PlannerClient = {
  async registerDataset() {
    return { dataset_id: "preview" };
  },
  async ask({ question, columns }) {
    await wait(PREVIEW_DELAY_MS);
    const clarification = getPrototypeClarification(question, columns);
    if (clarification) {
      return { status: "clarification", clarification };
    }
    return { status: "plan", plan: createPrototypeAnalysisPlan(question) };
  },
  async preprocess() {
    await wait(PREVIEW_DELAY_MS);
    return { status: "report", report: prototypeReport() };
  },
  async analyze() {
    await wait(CHAIN_DELAY_MS);
    return { status: "analysis", analysis: prototypeAnalysis() };
  },
  async interpret() {
    await wait(CHAIN_DELAY_MS);
    return { status: "interpretation", interpretation: prototypeInterpretation() };
  },
  async critique() {
    await wait(CHAIN_DELAY_MS);
    return { status: "critique", critique: prototypeCritique() };
  },
  async present() {
    await wait(CHAIN_DELAY_MS);
    return { status: "answer", answer: prototypeAnswer() };
  },
};

function prototypeReport(): PreprocessingReport {
  return {
    changes: ["prepare (select_columns): Kept the columns used by the question."],
    affectedColumns: ["species"],
    rowsBefore: 2,
    rowsAfter: 2,
    warnings: [],
  };
}

function prototypeAnalysis(): AnalysisReport {
  return {
    steps: [
      {
        id: "compare",
        method: "group_aggregate",
        sampleSize: 2,
        detail: "2 groups",
        warnings: [],
      },
    ],
    figures: [],
    warnings: [],
    results: [],
    artifacts: [],
  };
}

const preparedFinding = {
  claim: "The question can use the prepared columns.",
  resultIds: ["compare"],
};

function prototypeInterpretation(): InterpretationView {
  return {
    summary: "The prepared columns can be compared.",
    findings: [preparedFinding],
    limitations: [],
    unanswered: [],
    source: { summary: "The prepared columns can be compared." },
  };
}

function prototypeCritique(): CritiqueView {
  return {
    decision: "approved",
    issues: [],
    requiredChanges: [],
    source: { decision: "approved" },
  };
}

function prototypeAnswer(): ChatAnswer {
  return {
    text: "The prepared columns can be compared.",
    findings: [preparedFinding],
    limitations: [],
    figureIds: [],
    followUps: [],
  };
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
