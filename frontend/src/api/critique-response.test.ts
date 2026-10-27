import { describe, expect, it } from "vitest";

import { mapCritiquePayload } from "@/api/critique-response";

describe("mapCritiquePayload", () => {
  it("maps a critic error", () => {
    expect(
      mapCritiquePayload({
        status: "error",
        message: "The critic could not review the answer",
      }),
    ).toEqual({
      status: "error",
      message: "The critic could not review the answer",
    });
  });
});
