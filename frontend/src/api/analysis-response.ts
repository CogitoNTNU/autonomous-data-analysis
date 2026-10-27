import { count } from "@/api/payload/count";
import { errorStatus } from "@/api/payload/error-status";
import { isRecord } from "@/api/payload/is-record";
import { records } from "@/api/payload/records";
import { requiredText } from "@/api/payload/required-text";
import type { AnalysisReport } from "@/types/planner";

export type AnalysisResult =
  | { status: "analysis"; analysis: AnalysisReport }
  | { status: "error"; message: string };

export function mapAnalysisPayload(payload: unknown): AnalysisResult {
  const failure = errorStatus(payload, "Analysis");
  if (failure) {
    return failure;
  }
  return { status: "analysis", analysis: toAnalysis(payload) };
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
    id: requiredText(result.step_id, "Analysis"),
    method: requiredText(result.method, "Analysis"),
    sampleSize: count(result.sample_size, "Analysis"),
    detail: describe(result.values),
    warnings: warningMessages(result.warnings),
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

function trimNumber(value: number): string {
  if (Number.isInteger(value)) {
    return String(value);
  }
  return String(Math.round(value * 100) / 100);
}
