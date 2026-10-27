import type { WorkflowClient, WorkflowSnapshot } from "@/api/workflows";
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
// Demo-only client. Production uses the persisted backend harness.
const previews = new Map<string, WorkflowSnapshot>();
export const prototypePlanner: WorkflowClient = {
  async registerDataset() { return { dataset_id: "preview" }; },
  async start({ question, columns }) {
    await wait(PREVIEW_DELAY_MS);
    const clarification = getPrototypeClarification(question, columns);
    const result: WorkflowSnapshot = {
      runId: crypto.randomUUID(), checkpointId: "preview", status: clarification ? "needs_clarification" : "running",
      activeAgent: "planner", question: clarification?.question ?? null,
      plan: clarification ? null : createPrototypeAnalysisPlan(question),
      report: null, analysis: null, interpretation: null, critique: null, answer: null, error: null,
    };
    previews.set(result.runId, result);
    return result;
  },
  async resume({ runId, answer }) {
    await wait(PREVIEW_DELAY_MS);
    const result = { ...preview(runId), status: "running" as const, question: null, plan: createPrototypeAnalysisPlan(answer) };
    previews.set(runId, result);
    return result;
  },
  async status(runId) {
    return { ...preview(runId), status: "completed", activeAgent: null,
      report: prototypeReport(), analysis: prototypeAnalysis(), interpretation: prototypeInterpretation(),
      critique: prototypeCritique(), answer: prototypeAnswer(),
    };
  },
};
function preview(runId: string): WorkflowSnapshot {
  const result = previews.get(runId);
  if (!result) throw new Error("Unknown preview");
  return result;
}

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
