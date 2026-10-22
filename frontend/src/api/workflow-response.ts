import type {
  AnalysisReport,
  ChatAnswer,
  CritiqueView,
  InterpretationView,
} from "@/types/planner";

export type AnalysisResult =
  | { status: "analysis"; analysis: AnalysisReport }
  | { status: "error"; message: string };

export type InterpretationResult =
  | { status: "interpretation"; interpretation: InterpretationView }
  | { status: "error"; message: string };

export type CritiqueResult =
  | { status: "critique"; critique: CritiqueView }
  | { status: "error"; message: string };

export type AnswerResult =
  | { status: "answer"; answer: ChatAnswer }
  | { status: "error"; message: string };

export function mapAnalysisPayload(payload: unknown): AnalysisResult {
  const failure = errorStatus(payload, "Analysis");
  if (failure) {
    return failure;
  }
  return { status: "analysis", analysis: toAnalysis(payload) };
}

export function mapInterpretationPayload(payload: unknown): InterpretationResult {
  const failure = errorStatus(payload, "Interpretation");
  if (failure) {
    return failure;
  }
  return {
    status: "interpretation",
    interpretation: toInterpretation(field(payload, "interpretation")),
  };
}

export function mapCritiquePayload(payload: unknown): CritiqueResult {
  const failure = errorStatus(payload, "Critic");
  if (failure) {
    return failure;
  }
  return { status: "critique", critique: toCritique(field(payload, "critique")) };
}

export function mapAnswerPayload(payload: unknown): AnswerResult {
  const failure = errorStatus(payload, "Chat");
  if (failure) {
    return failure;
  }
  return { status: "answer", answer: toAnswer(field(payload, "answer")) };
}

function errorStatus(
  payload: unknown,
  name: string,
): { status: "error"; message: string } | null {
  if (!isRecord(payload) || typeof payload.status !== "string") {
    throw new Error(`${name} returned an unreadable response`);
  }
  if (payload.status === "error") {
    return { status: "error", message: text(payload.message, name) };
  }
  if (payload.status !== "success") {
    throw new Error(`${name} returned an unknown status`);
  }
  return null;
}

function field(payload: unknown, key: string): unknown {
  if (!isRecord(payload)) {
    return undefined;
  }
  return payload[key];
}

function toAnalysis(value: unknown): AnalysisReport {
  if (!isRecord(value)) {
    throw new Error("Analysis returned no results");
  }
  const results = records(value.results, "Analysis");
  return {
    steps: results.map(toStep),
    figures: figures(value.figures),
    warnings: warningMessages(value.warnings),
    results,
    artifacts: artifacts(value.artifacts),
  };
}

function toStep(result: Record<string, unknown>) {
  return {
    id: text(result.step_id, "Analysis"),
    method: text(result.method, "Analysis"),
    sampleSize: count(result.sample_size, "Analysis"),
    detail: describe(result.values),
    warnings: warningMessages(result.warnings),
  };
}

function toInterpretation(value: unknown): InterpretationView {
  if (!isRecord(value)) {
    throw new Error("Interpretation returned no summary");
  }
  return {
    summary: text(value.summary, "Interpretation"),
    findings: findings(value.findings),
    limitations: stringList(value.limitations),
    unanswered: stringList(value.unanswered_questions),
    source: value,
  };
}

function toCritique(value: unknown): CritiqueView {
  if (!isRecord(value) || !isDecision(value.decision)) {
    throw new Error("Critic returned no decision");
  }
  return {
    decision: value.decision,
    issues: issues(value.issues),
    requiredChanges: stringList(value.required_changes),
    source: value,
  };
}

function toAnswer(value: unknown): ChatAnswer {
  if (!isRecord(value)) {
    throw new Error("Chat returned no answer");
  }
  return {
    text: text(value.text, "Chat"),
    followUps: stringList(value.follow_up_suggestions),
  };
}

function describe(values: unknown): string {
  if (!isRecord(values)) {
    return "Result stored.";
  }
  if (typeof values.error === "string" && values.error.trim()) {
    return values.error;
  }
  if (isRecord(values.columns)) {
    const parts = Object.entries(values.columns).map(([name, stats]) => {
      if (!isRecord(stats) || typeof stats.mean !== "number") {
        return name;
      }
      return `${name} mean ${trimNumber(stats.mean)}`;
    });
    if (parts.length > 0) {
      return parts.join(", ");
    }
  }
  if (Array.isArray(values.groups)) {
    return `${values.groups.length} groups`;
  }
  return "Result stored.";
}

function figures(value: unknown): AnalysisReport["figures"] {
  return records(value, "Analysis").flatMap((figure) => {
    const id = figure.artifact_id;
    const image = figure.image;
    if (typeof id !== "string" || typeof image !== "string") {
      return [];
    }
    if (!image.startsWith("data:image/png;base64,")) {
      return [];
    }
    return [{ id, image }];
  });
}

function artifacts(value: unknown): AnalysisReport["artifacts"] {
  return records(value, "Analysis").flatMap((artifact) => {
    const id = artifact.artifact_id;
    const type = artifact.type;
    if (typeof id !== "string" || typeof type !== "string") {
      return [];
    }
    return [{ artifact_id: id, type }];
  });
}

function findings(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item) || typeof item.claim !== "string" || !item.claim.trim()) {
      return [];
    }
    return [item.claim];
  });
}

function issues(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item) || typeof item.description !== "string") {
      return [];
    }
    return [item.description];
  });
}

function warningMessages(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (typeof item === "string" && item.trim()) {
      return [item];
    }
    if (isRecord(item) && typeof item.message === "string" && item.message.trim()) {
      return [item.message];
    }
    return [];
  });
}

function records(value: unknown, name: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    throw new Error(`${name} returned an unreadable response`);
  }
  return value.filter(isRecord);
}

function isDecision(value: unknown): value is CritiqueView["decision"] {
  return value === "approved" || value === "revise" || value === "cannot_complete";
}

function count(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${name} returned an unreadable response`);
  }
  return value;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function text(value: unknown, name: string): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${name} left a required field empty`);
  }
  return value;
}

function trimNumber(value: number): string {
  if (Number.isInteger(value)) {
    return String(value);
  }
  return String(Math.round(value * 100) / 100);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
