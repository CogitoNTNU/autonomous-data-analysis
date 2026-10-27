import { afterEach, describe, expect, it, vi } from "vitest";

import { browserPlanner } from "@/api/planner";
import type { AnswerAsk } from "@/api/planner-client";

const input: AnswerAsk = {
  interpretation: {
    summary: "Older penguins weigh more.",
    findings: [
      { claim: "Mass rises with age.", resultIds: ["r1"] },
      { claim: "Unsupported.", resultIds: [] },
    ],
    limitations: ["Only 40 rows were complete."],
    unanswered: ["Which island?"],
    source: { summary: "Older penguins weigh more.", extra: true },
  },
  critique: {
    decision: "approved",
    issues: ["not sent"],
    requiredChanges: [],
    source: { decision: "approved" },
  },
  artifacts: [
    { artifact_id: "heatmap-1", type: "figure", storage_ref: "x.png" },
    { artifact_id: "t1", type: "table" },
    { artifact_id: "note", type: "note" },
  ] as AnswerAsk["artifacts"],
};

describe("browserPlanner.present", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends findings and artifact ids without chart bytes or extra keys", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: "success",
          answer: {
            text: "Older penguins weigh more.",
            findings: [],
            limitations: [],
            artifact_ids: ["heatmap-1"],
            follow_up_suggestions: [],
          },
        }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await browserPlanner.present(input);

    const call = fetchMock.mock.calls[0] as [string, { body?: string }] | undefined;
    expect(call?.[0]).toBe("/api/chat");
    expect(JSON.parse(call?.[1].body ?? "")).toEqual({
      interpretation: {
        summary: "Older penguins weigh more.",
        findings: [{ claim: "Mass rises with age.", result_ids: ["r1"] }],
        limitations: ["Only 40 rows were complete."],
        unanswered_questions: ["Which island?"],
      },
      critique: { decision: "approved", required_changes: [] },
      artifacts: [
        { artifact_id: "heatmap-1", type: "figure" },
        { artifact_id: "t1", type: "table" },
      ],
    });
  });
});
