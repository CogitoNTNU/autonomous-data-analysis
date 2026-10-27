import { describe, expect, it, vi } from "vitest";

import type { InterpretationAsk, PlannerClient } from "@/api/planner";
import { continueReviewedPlan } from "@/features/analysis-chat/continue-reviewed-plan";
import { prototypePlanner } from "@/features/analysis-chat/prototype-planner";
import type { CritiqueView, InterpretationView, StoredPlan } from "@/types/planner";

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
const interpretation: InterpretationView = {
  summary: "Older penguins weigh more.",
  findings,
  limitations: [],
  unanswered: [],
  source: { summary: "Older penguins weigh more." },
};
const critique: CritiqueView = {
  decision: "approved",
  issues: [],
  requiredChanges: [],
  source: { decision: "approved" },
};

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
    const critiqueClient = vi.fn();
    const publish = vi.fn();
    await continueReviewedPlan({ ...prototypePlanner, critique: critiqueClient }, input, publish, "critic");
    expect(publish).toHaveBeenLastCalledWith(expect.objectContaining({ phase: "error", message: "Interpretation is required before review" }));
    expect(critiqueClient).not.toHaveBeenCalled();
  });

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

    await continueReviewedPlan(
      client(present),
      { ...ask(), artifacts },
      () => undefined,
      "chat",
      interpretation,
      critique,
    );

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
    preprocess: vi.fn(),
    analyze: vi.fn(),
    interpret: vi.fn(),
    critique: vi.fn(),
    present,
  };
}
