import { errorStatus } from "@/api/payload/error-status";
import { field } from "@/api/payload/field";
import { isRecord } from "@/api/payload/is-record";
import { requiredText } from "@/api/payload/required-text";
import { stringList } from "@/api/payload/string-list";
import type { InterpretationView } from "@/types/planner";

export type InterpretationResult =
  | { status: "interpretation"; interpretation: InterpretationView }
  | { status: "error"; message: string };

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

function toInterpretation(value: unknown): InterpretationView {
  if (!isRecord(value)) {
    throw new Error("Interpretation returned no summary");
  }
  return {
    summary: requiredText(value.summary, "Interpretation"),
    findings: findings(value.findings),
    limitations: stringList(value.limitations),
    unanswered: stringList(value.unanswered_questions),
    source: value,
  };
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
