import { describe, expect, it } from "vitest";

import { mapAnswerPayload } from "@/api/answer-response";

const answer = {
  text: "One row remains.",
  findings: [{ claim: "Age is 20.", result_ids: ["summarize"] }],
  limitations: ["The sample is small."],
  artifact_ids: ["heatmap-1"],
  follow_up_suggestions: ["Why?"],
};

describe("mapAnswerPayload", () => {
  it("maps findings, limitations, and figure ids", () => {
    expect(mapAnswerPayload({ status: "success", answer })).toEqual({
      status: "answer",
      answer: {
        text: "One row remains.",
        findings: [{ claim: "Age is 20.", resultIds: ["summarize"] }],
        limitations: ["The sample is small."],
        figureIds: ["heatmap-1"],
        followUps: ["Why?"],
      },
    });
  });

  it("rejects an empty answer", () => {
    expect(() =>
      mapAnswerPayload({ status: "success", answer: { ...answer, text: " " } }),
    ).toThrow(/required field empty/);
  });

  it("rejects an answer that omits findings, limitations, or charts", () => {
    for (const key of ["findings", "limitations", "artifact_ids"] as const) {
      const incomplete = { ...answer };
      delete incomplete[key];
      expect(() => mapAnswerPayload({ status: "success", answer: incomplete })).toThrow(
        /unreadable response/,
      );
    }
  });

  it("keeps an answer that names no charts", () => {
    expect(
      mapAnswerPayload({
        status: "success",
        answer: { ...answer, artifact_ids: [] },
      }),
    ).toMatchObject({
      answer: { figureIds: [], limitations: ["The sample is small."] },
    });
  });
});
