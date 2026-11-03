import { describe, expect, it } from "vitest";
import type { WorkflowSnapshot } from "@/api/workflows";
import { archiveRound } from "@/features/analysis-chat/analysis-rounds";

const answer = { text: "Mean age is 20", findings: [], limitations: [], figureIds: ["f1"], followUps: [] };
const figure = { id: "f1", image: "data:image/png;base64,abc" };
const completed: WorkflowSnapshot = {
  runId: "run-1", checkpointId: "c1", status: "completed", activeAgent: null, question: null, plan: null, report: null,
  analysis: { steps: [], figures: [figure], warnings: [], results: [], artifacts: [] },
  interpretation: null, critique: null, answer, error: null, dialogue: [], analysisRound: 1, acceptsMessages: true,
};
const nextRound: WorkflowSnapshot = { ...completed, status: "running", analysis: null, answer: null, analysisRound: 2 };

describe("analysis rounds", () => {
  it("keeps the previous answer and charts when the next round starts", () => {
    expect(archiveRound([], completed, nextRound)).toEqual([{
      round: 1, answer, figures: [figure], tables: [], plan: null, report: null,
      analysis: completed.analysis, interpretation: null, critique: null,
    }]);
  });

  it("does not archive again while the next round is still running", () => {
    const rounds = archiveRound([], completed, nextRound);
    expect(archiveRound(rounds, nextRound, { ...nextRound, activeAgent: "analysis" })).toBe(rounds);
  });

  it("keeps rounds while dialogue continues in the same round", () => {
    const rounds = archiveRound([], completed, nextRound);
    expect(archiveRound(rounds, completed, { ...completed, checkpointId: "c2" })).toBe(rounds);
  });

  it("clears rounds for a different run or a first snapshot", () => {
    const rounds = archiveRound([], completed, nextRound);
    expect(archiveRound(rounds, nextRound, { ...nextRound, runId: "run-2" })).toEqual([]);
    expect(archiveRound(rounds, null, completed)).toEqual([]);
  });
});
