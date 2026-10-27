import { describe, expect, it } from "vitest";

import { mapAnswerPayload } from "@/api/answer-response";

describe("mapAnswerPayload", () => {
  it("maps the chat answer", () => {
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
