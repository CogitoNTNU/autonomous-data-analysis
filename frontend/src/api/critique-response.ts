import { errorStatus } from "@/api/payload/error-status";
import { field } from "@/api/payload/field";
import { isRecord } from "@/api/payload/is-record";
import { stringList } from "@/api/payload/string-list";
import type { CritiqueView } from "@/types/planner";

export type CritiqueResult =
  | { status: "critique"; critique: CritiqueView }
  | { status: "error"; message: string };

export function mapCritiquePayload(payload: unknown): CritiqueResult {
  const failure = errorStatus(payload, "Critic");
  if (failure) {
    return failure;
  }
  return { status: "critique", critique: toCritique(field(payload, "critique")) };
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

function isDecision(value: unknown): value is CritiqueView["decision"] {
  return value === "approved" || value === "revise" || value === "cannot_complete";
}
