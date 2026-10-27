import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import type { AnalysisFigure, ChatAnswer } from "@/types/planner";

const figures: AnalysisFigure[] = [
  { id: "heatmap-1", image: "data:image/png;base64,abc" },
];

const answer: ChatAnswer = {
  text: "Older penguins weigh more.",
  findings: [{ claim: "Mass rises with age.", resultIds: ["r1"] }],
  limitations: ["Only 40 rows were complete."],
  figureIds: ["heatmap-1", "missing-chart"],
  followUps: ["Which island?"],
};

describe("ChatAnswerCard", () => {
  it("shows the answer immediately and still collapses from the keyboard", async () => {
    const user = userEvent.setup();
    render(<ChatAnswerCard answer={answer} figures={figures} />);

    const toggle = screen.getByRole("button", { name: "Prepared an answer" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Older penguins weigh more.")).toBeVisible();
    expect(screen.getByText("Mass rises with age.")).toBeVisible();
    expect(screen.getByRole("img", { name: "Analysis chart" })).toHaveAttribute(
      "src",
      "data:image/png;base64,abc",
    );
    expect(screen.getByText("This chart could not be loaded")).toBeVisible();
    expect(screen.getByText("Only 40 rows were complete.")).toBeVisible();
    expect(screen.getByText("Which island?")).toBeVisible();
    expect(readingOrder()).toEqual([
      "Older penguins weigh more.",
      "Mass rises with age.",
      "This chart could not be loaded",
      "Only 40 rows were complete.",
      "Which island?",
    ]);

    toggle.focus();
    await user.keyboard("{Enter}");

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Older penguins weigh more.")).toBeNull();
    expect(screen.queryByRole("img", { name: "Analysis chart" })).toBeNull();
  });
});

function readingOrder(): string[] {
  const text = document.getElementById("ch-details")?.textContent ?? "";
  return [
    "Older penguins weigh more.",
    "Mass rises with age.",
    "This chart could not be loaded",
    "Only 40 rows were complete.",
    "Which island?",
  ].sort((left, right) => text.indexOf(left) - text.indexOf(right));
}
