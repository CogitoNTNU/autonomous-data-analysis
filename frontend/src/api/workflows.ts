import { mapAnalysisPayload } from "@/api/analysis-response";
import { mapAnswerPayload } from "@/api/answer-response";
import { mapCritiquePayload } from "@/api/critique-response";
import { mapInterpretationPayload } from "@/api/interpretation-response";
import { isRecord } from "@/api/payload/is-record";
import { requiredText } from "@/api/payload/required-text";
import { mapPlannerPayload } from "@/api/planner-response";
import { mapPreprocessingPayload } from "@/api/preprocessing-response";
import type { AnalysisPlan, AnalysisReport, ChatAnswer, CritiqueView, InterpretationView, PreprocessingReport } from "@/types/planner";

export type WorkflowAgent = "planner" | "preprocessing" | "analysis" | "interpretation" | "critic" | "chat";
export type WorkflowSnapshot = {
  runId: string;
  checkpointId: string;
  status: "running" | "needs_clarification" | "completed" | "error";
  activeAgent: WorkflowAgent | null;
  question: string | null;
  plan: AnalysisPlan | null;
  report: PreprocessingReport | null;
  analysis: AnalysisReport | null;
  interpretation: InterpretationView | null;
  critique: CritiqueView | null;
  answer: ChatAnswer | null;
  error: string | null;
};

export type WorkflowStart = { datasetId: string; question: string; columns: string[] };
export type WorkflowResume = { runId: string; checkpointId: string; answer: string };
export type WorkflowClient = {
  registerDataset: (file: File) => Promise<{ dataset_id: string }>;
  start: (input: WorkflowStart, signal?: AbortSignal) => Promise<WorkflowSnapshot>;
  status: (runId: string, signal?: AbortSignal) => Promise<WorkflowSnapshot>;
  resume: (input: WorkflowResume, signal?: AbortSignal) => Promise<WorkflowSnapshot>;
};

export const browserWorkflow: WorkflowClient = {
  async registerDataset(file) {
    const value = await request("/api/datasets", await file.text(), undefined, "text/csv");
    if (!isRecord(value)) throw new Error("The dataset was not registered");
    return { dataset_id: requiredText(value.dataset_id, "Dataset") };
  },
  async start(input, signal) {
    return mapWorkflow(await request("/api/workflows", JSON.stringify({
      dataset_id: input.datasetId, question: input.question,
    }), signal));
  },
  async status(runId, signal) {
    return mapWorkflow(await request("/api/workflows/status", JSON.stringify({ run_id: runId }), signal));
  },
  async resume(input, signal) {
    return mapWorkflow(await request("/api/workflows/resume", JSON.stringify({
      run_id: input.runId, checkpoint_id: input.checkpointId, answer: input.answer,
    }), signal));
  },
};

export function mapWorkflow(value: unknown): WorkflowSnapshot {
  if (!isRecord(value) || !isStatus(value.status)) throw new Error("Unreadable workflow status");
  if (value.active_agent !== null && !isAgent(value.active_agent)) throw new Error("Unknown workflow agent");
  const plan = value.plan === null ? null : mapPlannerPayload({ status: "success", plan: value.plan });
  const report = value.report === null ? null : mapPreprocessingPayload({ status: "success", report: value.report });
  const analysis = value.analysis === null ? null : mapAnalysisPayload(isRecord(value.analysis) ? { ...value.analysis, status: "success" } : value.analysis);
  const interpretation = value.interpretation === null ? null : mapInterpretationPayload({ status: "success", interpretation: value.interpretation });
  const critique = value.critique === null ? null : mapCritiquePayload({ status: "success", critique: value.critique });
  const answer = value.answer === null ? null : mapAnswerPayload({ status: "success", answer: value.answer });
  if ((plan && plan.status !== "plan") || (report && report.status !== "report") || (analysis && analysis.status !== "analysis") || (interpretation && interpretation.status !== "interpretation") || (critique && critique.status !== "critique") || (answer && answer.status !== "answer")) throw new Error("Invalid workflow output");
  if (value.status === "completed" && !answer) throw new Error("The completed workflow has no answer");
  return {
    runId: requiredText(value.run_id, "Workflow"),
    checkpointId: requiredText(value.checkpoint_id, "Workflow"),
    status: value.status,
    activeAgent: value.active_agent,
    question: value.question === null ? null : requiredText(value.question, "Workflow"),
    plan: plan?.status === "plan" ? plan.plan : null,
    report: report?.status === "report" ? report.report : null,
    analysis: analysis?.status === "analysis" ? analysis.analysis : null,
    interpretation: interpretation?.status === "interpretation" ? interpretation.interpretation : null,
    critique: critique?.status === "critique" ? critique.critique : null,
    answer: answer?.status === "answer" ? answer.answer : null,
    error: value.error === null ? null : requiredText(isRecord(value.error) ? value.error.message : null, "Workflow"),
  };
}

function isAgent(value: unknown): value is WorkflowAgent {
  return typeof value === "string" && ["planner", "preprocessing", "analysis", "interpretation", "critic", "chat"].includes(value);
}
function isStatus(value: unknown): value is WorkflowSnapshot["status"] {
  return value === "running" || value === "needs_clarification" || value === "completed" || value === "error";
}
async function request(path: string, body: string, signal?: AbortSignal, contentType = "application/json"): Promise<unknown> {
  const response = await fetch(path, { method: "POST", headers: { "Content-Type": contentType }, body, signal });
  const text = await response.text();
  let value: unknown;
  try { value = JSON.parse(text); } catch { throw new Error("The backend returned an empty or unreadable response"); }
  if (!response.ok) throw new Error(isRecord(value) && typeof value.message === "string" ? value.message : "The workflow could not be reached");
  return value;
}
