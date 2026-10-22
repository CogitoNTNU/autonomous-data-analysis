import { describe, expect, it } from "vitest";

import { mapPlannerPayload } from "@/api/planner-response";

describe("mapPlannerPayload", () => {
  it("turns planner steps into the plan card", () => {
    const result = mapPlannerPayload({
      status: "success",
      plan: {
        plan_id: "plan-1",
        objective: "Compare average body mass",
        assumptions: ["Species names are complete."],
        preprocessing_steps: [],
        analysis_steps: [
          {
            step_id: "mass",
            tool_name: "group_aggregate",
            arguments: { group_by: ["species"] },
          },
        ],
        expected_outputs: ["Average body mass for each species"],
      },
    });

    expect(result).toEqual({
      status: "plan",
      plan: {
        id: "plan-1",
        objective: "Compare average body mass",
        assumptions: ["Species names are complete."],
        status: "draft",
        source: {
          plan_id: "plan-1",
          objective: "Compare average body mass",
          required_columns: [],
          preprocessing_steps: [],
          analysis_steps: [
            {
              step_id: "mass",
              tool_name: "group_aggregate",
              arguments: { group_by: ["species"] },
              depends_on: [],
            },
          ],
          expected_outputs: ["Average body mass for each species"],
          assumptions: ["Species names are complete."],
        },
        steps: [
          {
            id: "mass",
            title: "group aggregate",
            description: 'group_by: ["species"]',
          },
          {
            id: "expected-output",
            title: "Expected output",
            description: "Average body mass for each species",
          },
        ],
      },
    });
  });

  it("rejects a response without a status", () => {
    expect(() => mapPlannerPayload({ plan: {} })).toThrow(
      "unreadable response",
    );
  });

  it("keeps a clarification as one question to answer", () => {
    const result = mapPlannerPayload({
      status: "needs_clarification",
      question: "Which size measure should be used?",
    });

    expect(result.status).toBe("clarification");
    if (result.status !== "clarification") {
      return;
    }
    expect(result.clarification.question).toBe(
      "Which size measure should be used?",
    );
    expect(result.clarification.options).toEqual([]);
  });
});
