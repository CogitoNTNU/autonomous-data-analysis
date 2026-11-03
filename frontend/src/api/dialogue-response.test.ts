import { describe, expect, it } from "vitest";
import { mapDialogue } from "@/api/dialogue-response";

const turn = {
  role: "assistant", content: "Rows without age were removed.", analysis_round: 1,
  referenced_ids: ["drop-missing"], starts_analysis: false, failed: false,
};

describe("dialogue mapping", () => {
  it("maps follow-up turns to browser fields", () => {
    expect(mapDialogue([turn, { ...turn, role: "user", content: "Why?", referenced_ids: [] }])).toEqual([
      { role: "assistant", content: turn.content, analysisRound: 1, referencedIds: ["drop-missing"], startsAnalysis: false, failed: false },
      { role: "user", content: "Why?", analysisRound: 1, referencedIds: [], startsAnalysis: false, failed: false },
    ]);
  });

  it("accepts an empty dialogue", () => {
    expect(mapDialogue([])).toEqual([]);
  });

  it.each([
    ["a missing list", undefined],
    ["an unknown role", [{ ...turn, role: "system" }]],
    ["an empty message", [{ ...turn, content: " " }]],
    ["an invalid round", [{ ...turn, analysis_round: 0 }]],
  ])("rejects %s", (_, value) => {
    expect(() => mapDialogue(value)).toThrow();
  });
});
