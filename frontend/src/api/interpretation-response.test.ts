import { describe, expect, it } from "vitest";

import { mapInterpretationPayload } from "@/api/interpretation-response";

describe("mapInterpretationPayload", () => {
  it("maps an interpretation", () => {
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
  });
});
