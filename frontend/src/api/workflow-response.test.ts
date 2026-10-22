import { describe, expect, it } from "vitest";

import {
  mapAnalysisPayload,
  mapAnswerPayload,
  mapCritiquePayload,
  mapInterpretationPayload,
} from "@/api/workflow-response";

const result = {
  step_id: "summarize",
  method: "descriptive_statistics",
  sample_size: 1,
  values: { columns: { age: { mean: 20 } }, status: "partial" },
  warnings: [{ message: "age n=1" }],
};

describe("workflow responses", () => {
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

  it("maps an interpretation, a critic decision, and the chat answer", () => {
    expect(
      mapInterpretationPayload({
        status: "success",
        interpretation: {
          summary: "One row remains.",
          findings: [{ claim: "Age is 20.", result_ids: ["summarize"] }],
          limitations: ["The sample is small."],
          unanswered_questions: [],
        },
      }),
    ).toMatchObject({
      interpretation: {
        summary: "One row remains.",
        findings: ["Age is 20."],
        limitations: ["The sample is small."],
      },
    });
    expect(
      mapCritiquePayload({
        status: "error",
        message: "The critic could not review the answer",
      }),
    ).toEqual({
      status: "error",
      message: "The critic could not review the answer",
    });
    expect(
      mapAnswerPayload({
        status: "success",
        answer: { text: "One row remains.", follow_up_suggestions: ["Why?"] },
      }),
    ).toEqual({
      status: "answer",
      answer: { text: "One row remains.", followUps: ["Why?"] },
    });
  });
});
