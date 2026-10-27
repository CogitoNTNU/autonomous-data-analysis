import { describe, expect, it, vi } from "vitest";

import type { PlannerClient } from "@/api/planner";
import { continueReviewedPlan } from "@/features/analysis-chat/continue-reviewed-plan";
import type { StoredPlan } from "@/types/planner";

const findings = [{ claim: "Mass rises with age.", resultIds: ["r1"] }];
const artifacts = [
  { artifact_id: "heatmap-1", type: "figure" },
  { artifact_id: "t1", type: "table" },
];
const plan: StoredPlan = {
  plan_id: "plan-1",
  objective: "Compare mass",
  required_columns: ["mass"],
  preprocessing_steps: [],
  analysis_steps: [],
  expected_outputs: [],
  assumptions: [],
};

describe("continueReviewedPlan", () => {
  it("passes analysis artifacts and findings to present without chart bytes", async () => {
    const present = vi.fn().mockResolvedValue({
      status: "answer",
      answer: {
        text: "Older penguins weigh more.",
        findings,
        limitations: [],
        figureIds: ["heatmap-1"],
        followUps: [],
      },
    });

    await continueReviewedPlan(client(present), ask(), () => undefined);

    expect(present).toHaveBeenCalledWith(
      expect.objectContaining({
        artifacts,
        interpretation: expect.objectContaining({ findings }),
      }),
    );
    expect(JSON.stringify(present.mock.calls[0]?.[0])).not.toContain("base64");
  });
});

function ask() {
  return {
    datasetId: "dataset-1",
    csv: "mass\n1",
    plan,
    question: "Compare mass",
    results: [],
    artifacts: [],
  };
}

function client(present: PlannerClient["present"]): PlannerClient {
  return {
    registerDataset: vi.fn(),
    ask: vi.fn(),
    preprocess: vi.fn().mockResolvedValue({
      status: "report",
      report: {
        changes: [],
        affectedColumns: [],
        rowsBefore: 1,
        rowsAfter: 1,
        warnings: [],
      },
    }),
    analyze: vi.fn().mockResolvedValue({
      status: "analysis",
      analysis: {
        steps: [],
        figures: [{ id: "heatmap-1", image: "data:image/png;base64,abc" }],
        warnings: [],
        results: [{ step_id: "r1" }],
        artifacts,
      },
    }),
    interpret: vi.fn().mockResolvedValue({
      status: "interpretation",
      interpretation: {
        summary: "Older penguins weigh more.",
        findings,
        limitations: [],
        unanswered: [],
        source: { summary: "Older penguins weigh more." },
      },
    }),
    critique: vi.fn().mockResolvedValue({
      status: "critique",
      critique: {
        decision: "approved",
        issues: [],
        requiredChanges: [],
        source: { decision: "approved" },
      },
    }),
    present,
  };
}
