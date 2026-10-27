import { describe, expect, it } from "vitest";

import { mapAnalysisPayload } from "@/api/analysis-response";

const result = {
  step_id: "summarize",
  method: "descriptive_statistics",
  sample_size: 1,
  values: { columns: { age: { mean: 20 } }, status: "partial" },
  warnings: [{ message: "age n=1" }],
};

describe("mapAnalysisPayload", () => {
  it("describes calculated columns and keeps the raw result", () => {
    const mapped = mapAnalysisPayload({
      status: "success",
      results: [result],
      artifacts: [],
      figures: [],
      warnings: ["age n=1"],
    });

    expect(mapped).toMatchObject({
      status: "analysis",
      analysis: {
        steps: [
          {
            id: "summarize",
            method: "descriptive_statistics",
            sampleSize: 1,
            detail: "age mean 20",
            warnings: ["age n=1"],
          },
        ],
      },
    });
  });

  it("rejects an analysis response without results", () => {
    expect(() => mapAnalysisPayload({ status: "success" })).toThrow(
      /unreadable response/,
    );
  });

  it("keeps an empty analysis when the plan has no analysis steps", () => {
    const mapped = mapAnalysisPayload({
      status: "success",
      results: [],
      artifacts: [],
      figures: [],
      warnings: [],
    });

    expect(mapped).toMatchObject({ analysis: { steps: [] } });
  });
});
