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


describe("grouped summary tables", () => {
  const grouped = {
    step_id: "groups", method: "group_aggregate", sample_size: 342,
    values: { status: "ok", group_count: 3, group_sizes: [123, 68, 151], groups: [
      { species: "Gentoo", mean_mass_g: 5076.016, mean_flipper_mm: 217.187 },
      { species: "Chinstrap", mean_mass_g: 3733.088, mean_flipper_mm: 195.824 },
      { species: "Adelie", mean_mass_g: 3700.662, mean_flipper_mm: 189.954 },
    ] }, warnings: [],
  };
  function payload(value: unknown) { return { status: "success", results: [value], artifacts: [], figures: [], warnings: [] }; }
  it("preserves the calculated values and group counts", () => {
    const mapped = mapAnalysisPayload(payload(grouped));
    expect(mapped).toMatchObject({ analysis: { tables: [{ sampleSize: 342, groupSizes: [123, 68, 151], columns: ["species", "mean_mass_g", "mean_flipper_mm"], rows: [["Gentoo", 5076.016, 217.187], ["Chinstrap", 3733.088, 195.824], ["Adelie", 3700.662, 189.954]] }] } });
  });
  it("rejects group counts that do not align with table rows", () => {
    expect(() => mapAnalysisPayload(payload({ ...grouped, values: { ...grouped.values, group_sizes: [342] } }))).toThrow("inconsistent group counts");
  });
  it("keeps failure reports readable when no grouped rows were produced", () => {
    expect(mapAnalysisPayload(payload({ ...grouped, values: { status: "failed", error: "Unavailable" } }))).toMatchObject({ analysis: { tables: [] } });
  });
});
