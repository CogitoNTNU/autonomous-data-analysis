import { count } from "@/api/payload/count";
import { isRecord } from "@/api/payload/is-record";
import { requiredText } from "@/api/payload/required-text";
import type { AnalysisTable } from "@/types/planner";

export function groupedTables(results: Record<string, unknown>[]): AnalysisTable[] {
  return results.flatMap((result) => {
    if (result.method !== "group_aggregate" || !isRecord(result.values) || result.values.status === "failed") return [];
    const groups = result.values.groups;
    if (!Array.isArray(groups) || !groups.every(isRecord)) throw new Error("Analysis returned an unreadable summary table");
    const columns = [...new Set(groups.flatMap((group) => Object.keys(group)))];
    const sizes = result.values.group_sizes;
    if (sizes !== undefined && (!Array.isArray(sizes) || sizes.length !== groups.length)) throw new Error("Analysis returned inconsistent group counts");
    return [{
      id: requiredText(result.step_id, "Analysis"),
      columns,
      rows: groups.map((group) => columns.map((column) => cell(group[column]))),
      sampleSize: count(result.sample_size, "Analysis"),
      groupSizes: sizes === undefined ? undefined : (sizes as unknown[]).map((value) => count(value, "Analysis")),
    }];
  });
}

function cell(value: unknown): string | number | boolean | null {
  if (value === undefined || value === null) return null;
  if (typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error("Analysis returned an unreadable table cell");
}
