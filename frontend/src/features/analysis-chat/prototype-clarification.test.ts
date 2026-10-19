import { describe, expect, it } from "vitest";

import { getPrototypeClarification } from "@/features/analysis-chat/prototype-clarification";

describe("getPrototypeClarification", () => {
  const sizeColumns = ["species", "body_mass_g", "flipper_length_mm"];

  it("returns a typed clarification for an ambiguous size question", () => {
    const clarification = getPrototypeClarification(
      "Which penguins are the largest?",
      sizeColumns,
    );

    expect(clarification).toMatchObject({
      reason: "ambiguous_objective",
      question: "What do you mean by “largest”?",
    });
    expect(clarification?.options.map((option) => option.label)).toEqual([
      "Body mass",
      "Flipper length",
      "I’ll explain it myself",
    ]);
  });

  it("does not request clarification for an unambiguous question", () => {
    expect(
      getPrototypeClarification(
        "What is the average body mass?",
        sizeColumns,
      ),
    ).toBeNull();
  });

  it("does not invent choices when the required columns are unavailable", () => {
    expect(
      getPrototypeClarification("Which values are largest?", ["value"]),
    ).toBeNull();
  });
});
