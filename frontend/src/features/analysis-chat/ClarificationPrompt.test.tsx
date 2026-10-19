import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClarificationPrompt } from "@/features/analysis-chat/ClarificationPrompt";
import type { ClarificationRequest } from "@/types/planner";

const clarification: ClarificationRequest = {
  reason: "ambiguous_objective",
  question: "Which measure should be used?",
  description: "Choose one measure.",
  options: [
    { id: "mass", label: "Body mass" },
    { id: "custom", label: "I’ll explain it myself" },
  ],
};

describe("ClarificationPrompt", () => {
  it("returns the selected typed option", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <ClarificationPrompt
        clarification={clarification}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Body mass" }));

    expect(onSelect).toHaveBeenCalledWith({ id: "mass", label: "Body mass" });
  });

  it("directs custom answers to the message field", () => {
    render(
      <ClarificationPrompt
        awaitingCustomAnswer
        clarification={clarification}
        onSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Explain what you mean in the message field below."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Body mass" })).toBeNull();
  });
});
