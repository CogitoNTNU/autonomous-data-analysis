import { mapPlannerPayload } from "@/api/planner-response";
import {
  mapPreprocessingPayload,
  type PreprocessResult,
} from "@/api/preprocessing-response";
import {
  mapAnalysisPayload,
  mapAnswerPayload,
  mapCritiquePayload,
  mapInterpretationPayload,
  type AnalysisResult,
  type AnswerResult,
  type CritiqueResult,
  type InterpretationResult,
} from "@/api/workflow-response";
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

export const browserPlanner: PlannerClient = {
  registerDataset,
  ask,
  preprocess,
  analyze,
  interpret,
  critique,
  present,
};

async function registerDataset(file: File): Promise<{ dataset_id: string }> {
  const payload = await post("/api/datasets", await file.text(), "text/csv");
  if (!isRegistration(payload)) {
    throw new Error("The dataset was not registered");
  }
  return payload;
}

async function ask(input: PlannerAsk): Promise<PlannerResult> {
  const payload = await post(
    "/api/planner",
    JSON.stringify({
      dataset_id: input.datasetId,
      question: input.question,
      messages: input.messages,
      csv: input.csv,
    }),
    "application/json",
  );
  return mapPlannerPayload(payload);
}

async function preprocess(input: PreprocessAsk): Promise<PreprocessResult> {
  const payload = await post(
    "/api/preprocessing",
    JSON.stringify({
      dataset_id: input.datasetId,
      csv: input.csv,
      plan: input.plan,
    }),
    "application/json",
  );
  return mapPreprocessingPayload(payload);
}

async function analyze(input: AnalysisAsk): Promise<AnalysisResult> {
  return mapAnalysisPayload(await postJson("/api/analysis", input));
}

async function interpret(input: InterpretationAsk): Promise<InterpretationResult> {
  return mapInterpretationPayload(await postJson("/api/interpretation", input));
}

async function critique(input: CritiqueAsk): Promise<CritiqueResult> {
  return mapCritiquePayload(await postJson("/api/critic", input));
}

async function present(input: AnswerAsk): Promise<AnswerResult> {
  return mapAnswerPayload(
    await postJson("/api/chat", {
      interpretation: {
        summary: input.interpretation.summary,
        limitations: input.interpretation.limitations,
        unanswered_questions: input.interpretation.unanswered,
      },
      critique: {
        decision: input.critique.decision,
        required_changes: input.critique.requiredChanges,
      },
    }),
  );
}

async function postJson(path: string, body: unknown): Promise<unknown> {
  return post(path, JSON.stringify(requestBody(body)), "application/json");
}

function wireRecord(value: unknown): unknown {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return value;
  }
  const source = Reflect.get(value, "source");
  if (typeof source === "object" && source !== null && !Array.isArray(source)) {
    return source;
  }
  return value;
}

function requestBody(body: unknown): unknown {
  if (typeof body !== "object" || body === null) {
    return body;
  }
  if ("datasetId" in body && "plan" in body) {
  return {
    dataset_id: Reflect.get(body, "datasetId"),
    csv: Reflect.get(body, "csv"),
    plan: Reflect.get(body, "plan"),
    question: Reflect.get(body, "question"),
    results: Reflect.get(body, "results"),
    artifacts: Reflect.get(body, "artifacts"),
    interpretation: wireRecord(Reflect.get(body, "interpretation")),
    critique: wireRecord(Reflect.get(body, "critique")),
  };
  }
  return body;
}

async function post(path: string, body: string, contentType: string): Promise<unknown> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": contentType },
    body,
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    throw new Error(messageFrom(payload));
  }
  return payload;
}

function isRegistration(payload: unknown): payload is { dataset_id: string } {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }
  return typeof Reflect.get(payload, "dataset_id") === "string";
}

function messageFrom(payload: unknown): string {
  if (typeof payload === "object" && payload !== null) {
    const message = Reflect.get(payload, "message");
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return "The planner could not be reached";
}
