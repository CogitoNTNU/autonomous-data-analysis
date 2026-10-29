import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import type { AnalysisFigure, ChatAnswer } from "@/types/planner";

const figures: AnalysisFigure[] = [{ id: "heatmap-1", image: "data:image/png;base64,abc" }];
const answer: ChatAnswer = {
  text: "Gentoo have the greatest mean mass among the three species in this dataset.",
  findings: [{ claim: "The mean mass is 5,076 g.", resultIds: ["r1"] }],
  limitations: ["Descriptive averages do not establish statistical significance."],
  figureIds: ["heatmap-1", "missing-chart"], followUps: ["Which island?"],
};

describe("ChatAnswerCard", () => {
  it("shows the answer, evidence and limitations immediately", () => {
    render(<ChatAnswerCard answer={answer} figures={figures} />);
    expect(screen.getByText(answer.text)).toBeVisible();
    expect(screen.getByText("The mean mass is 5,076 g.")).toBeVisible();
    expect(screen.getByRole("img", { name: "Analysis chart 1" })).toHaveAttribute("src", "data:image/png;base64,abc");
    expect(screen.getByText("This chart could not be loaded")).toBeVisible();
    expect(screen.getByText(answer.limitations[0])).toBeVisible();
    expect(screen.queryByRole("button", { name: "Prepared an answer" })).toBeNull();
    expect(screen.getByText("Which island?")).not.toBeVisible();
  });

  it("deduplicates repeated claims and notes without changing their text", () => {
    render(<ChatAnswerCard answer={{ ...answer, figureIds: [], findings: [{ claim: answer.text, resultIds: ["r1"] }], limitations: [answer.limitations[0], answer.limitations[0]] }} figures={[]} />);
    expect(screen.getAllByText(answer.text)).toHaveLength(1);
    expect(screen.getAllByText(answer.limitations[0])).toHaveLength(1);
  });

  it("keeps additional findings and follow-up questions available on demand", async () => {
    const user = userEvent.setup();
    const findings = [1, 2, 3, 4].map((n) => ({ claim: `Finding ${n}`, resultIds: ["r1"] }));
    render(<ChatAnswerCard answer={{ ...answer, figureIds: [], findings }} figures={[]} />);
    expect(screen.getByText("Finding 3")).toBeVisible();
    expect(screen.getByText("Finding 4")).not.toBeVisible();
    await user.click(screen.getByText("More findings (1)"));
    expect(screen.getByText("Finding 4")).toBeVisible();
    await user.click(screen.getByText("Follow-up questions"));
    expect(screen.getByText("Which island?")).toBeVisible();
  });
});
