import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DialogueTurns } from "@/features/analysis-chat/DialogueTurns";
import type { DialogueTurn } from "@/types/dialogue";

const base = { analysisRound: 1, referencedIds: [], startsAnalysis: false, failed: false };

describe("DialogueTurns", () => {
  it("shows the user's message and the assistant's reply", () => {
    const turns: DialogueTurn[] = [
      { ...base, role: "user", content: "Why were rows removed?" },
      { ...base, role: "assistant", content: "Two rows had no age.", referencedIds: ["drop-missing"] },
    ];
    render(<DialogueTurns turns={turns} />);
    expect(screen.getByText("Why were rows removed?")).toBeVisible();
    expect(screen.getByText("Two rows had no age.")).toBeVisible();
    expect(screen.getByText("Data Analysis Planner")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("marks a failed reply as an alert without a new-analysis note", () => {
    render(<DialogueTurns turns={[{ ...base, role: "assistant", content: "Please try again.", failed: true, startsAnalysis: true }]} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Please try again.");
    expect(screen.queryByText("New analysis requested")).toBeNull();
  });

  it("renders nothing for an empty dialogue", () => {
    const { container } = render(<DialogueTurns turns={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
