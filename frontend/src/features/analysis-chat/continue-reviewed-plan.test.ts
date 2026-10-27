import { describe, expect, it, vi } from "vitest";

import type { InterpretationAsk } from "@/api/planner";
import { continueReviewedPlan } from "@/features/analysis-chat/continue-reviewed-plan";
import { prototypePlanner } from "@/features/analysis-chat/prototype-planner";

const input: InterpretationAsk = {
  datasetId: "dataset-1",
  csv: "city,amount\nOslo,1",
  plan: { plan_id: "plan-1", objective: "Compare amounts", required_columns: [], preprocessing_steps: [], analysis_steps: [], expected_outputs: [], assumptions: [] },
  question: "Compare amounts",
  results: [],
  artifacts: [],
};

describe("manual agent transitions", () => {
  it("stops at a failed stage without starting a downstream agent", async () => {
    const analyze = vi.fn();
    const publish = vi.fn();
    await continueReviewedPlan({
      ...prototypePlanner,
      preprocess: async () => ({ status: "error", message: "Invalid plan" }),
      analyze,
    }, input, publish);
    expect(publish).toHaveBeenLastCalledWith(expect.objectContaining({ phase: "error", message: "Invalid plan" }));
    expect(analyze).not.toHaveBeenCalled();
  });

  it("rejects a review without an interpretation", async () => {
    const critique = vi.fn();
    const publish = vi.fn();
    await continueReviewedPlan({ ...prototypePlanner, critique }, input, publish, "critic");
    expect(publish).toHaveBeenLastCalledWith(expect.objectContaining({ phase: "error", message: "Interpretation is required before review" }));
    expect(critique).not.toHaveBeenCalled();
  });
});
