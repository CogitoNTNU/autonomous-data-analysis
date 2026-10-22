import type { PreprocessingReport } from "@/types/planner";

export type PreprocessResult =
  | { status: "report"; report: PreprocessingReport }
  | { status: "error"; message: string };

export function mapPreprocessingPayload(payload: unknown): PreprocessResult {
  if (!isRecord(payload) || typeof payload.status !== "string") {
    throw new Error("Preprocessing returned an unreadable response");
  }
  if (payload.status === "error") {
    return { status: "error", message: text(payload.message) };
  }
  if (payload.status === "success") {
    return { status: "report", report: toReport(payload.report) };
  }
  throw new Error("Preprocessing returned an unknown status");
}

function toReport(value: unknown): PreprocessingReport {
  if (!isRecord(value)) {
    throw new Error("Preprocessing returned no report");
  }
  return {
    changes: stringList(value.changes),
    affectedColumns: stringList(value.affected_columns),
    rowsBefore: count(value.rows_before),
    rowsAfter: count(value.rows_after),
    warnings: warnings(value.warnings),
  };
}

function warnings(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item) || typeof item.message !== "string") {
      return [];
    }
    return [item.message];
  });
}

function count(value: unknown): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error("Preprocessing returned no row count");
  }
  return value;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

function text(value: unknown): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error("Preprocessing left a required field empty");
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
