import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WorkflowTurns } from "@/features/analysis-chat/WorkflowTurns";
import { createPrototypeAnalysisPlan } from "@/features/analysis-chat/prototype-plan";

type Session = Parameters<typeof WorkflowTurns>[0]["session"];
const session: Session = {
  busy: false, phase: "complete", error: null, canRetryReview: false, retryReview: () => {},
  plan: createPrototypeAnalysisPlan("Compare body mass"),
  report: { rowsBefore: 344, rowsAfter: 342, changes: ["Removed two incomplete rows."], affectedColumns: [], warnings: [] },
  analysis: null,
  interpretation: { summary: "Full internal interpretation", findings: [], limitations: [], unanswered: [], source: {} },
  critique: { decision: "approved", issues: [], requiredChanges: [], source: {} },
  answer: { text: "Gentoo have the greatest mean mass among these three species.", findings: [], limitations: ["Descriptive differences do not establish significance."], figureIds: [], followUps: [] },
  rounds: [], dialogue: [], analysisRound: 1, acceptsMessages: false, pendingMessage: null, submitQuestion: () => {},
};
const turn = { referencedIds: [], startsAnalysis: false, failed: false };
const emptyRound = { figures: [], tables: [], plan: null, report: null, analysis: null, interpretation: null, critique: null };

function follows(earlier: string, later: string) {
  const position = screen.getByText(earlier).compareDocumentPosition(screen.getByText(later));
  expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
}

describe("chronological workflow transcript", () => {
  it("shows each stage and then the answer beneath the critic", () => {
    render(<WorkflowTurns session={session} />);
    expect(screen.getByText(session.answer!.text)).toBeVisible();
    expect(screen.getByText(session.answer!.limitations[0])).toBeVisible();
    expect(screen.queryByText("Full internal interpretation")).toBeNull();
    expect(screen.queryByRole("button", { name: "View analysis details" })).toBeNull();
    follows("Planner", "PR");
    follows("PR", "CR");
    follows("Critic approved", session.answer!.text);
  });

  it("expands an agent card with the keyboard and preserves the main answer", async () => {
    const user = userEvent.setup();
    render(<WorkflowTurns session={session} />);
    const stage = screen.getByRole("button", { name: "Interpretation finished" });
    stage.focus();
    await user.keyboard("{Enter}");
    expect(stage).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Full internal interpretation")).toBeVisible();
    expect(document.getElementById(stage.getAttribute("aria-controls")!)).toBeVisible();
    await user.keyboard("{Enter}");
    expect(screen.queryByText("Full internal interpretation")).toBeNull();
    expect(screen.getByText(session.answer!.text)).toBeVisible();
  });

  it.each(["thinking", "analysis", "critic"] as const)("shows progress after the stages that have arrived during %s", (phase) => {
    render(<WorkflowTurns session={{ ...session, busy: true, phase, answer: null }} />);
    expect(screen.getAllByRole("status")).toHaveLength(1);
    follows("Critic approved", "Analyzing data…");
  });

  it("appends a new round after the earlier transcript", () => {
    const earlier = { ...emptyRound, round: 1, answer: { ...session.answer!, text: "Adelie are lightest." }, plan: createPrototypeAnalysisPlan("Earlier") };
    render(<WorkflowTurns session={{ ...session, busy: true, phase: "chat", rounds: [earlier], analysisRound: 2, pendingMessage: "Why Gentoo?", dialogue: [
      { ...turn, role: "user", content: "Compare Gentoo", analysisRound: 1 },
      { ...turn, role: "assistant", content: "Starting a comparison.", analysisRound: 1, startsAnalysis: true },
    ] }} />);
    const plans = screen.getAllByRole("button", { name: "Prepared an analysis plan, 3 steps" });
    expect(plans[0].compareDocumentPosition(screen.getByText("Adelie are lightest.")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    follows("Adelie are lightest.", "Compare Gentoo");
    expect(screen.getByText("Starting a comparison.").compareDocumentPosition(plans[1]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    follows(session.answer!.text, "Why Gentoo?");
    expect(screen.getByText("New analysis requested")).toBeVisible();
    follows("Why Gentoo?", "Writing a reply…");
  });

  it("offers follow-up questions only when the run accepts messages", async () => {
    const user = userEvent.setup();
    const submitQuestion = vi.fn();
    const answer = { ...session.answer!, followUps: ["Which island?"] };
    const { rerender } = render(<WorkflowTurns session={{ ...session, answer, acceptsMessages: true, submitQuestion }} />);
    await user.click(screen.getByRole("button", { name: "Which island?" }));
    expect(submitQuestion).toHaveBeenCalledWith("Which island?");
    rerender(<WorkflowTurns session={{ ...session, answer, busy: true, acceptsMessages: true, submitQuestion }} />);
    expect(screen.queryByRole("button", { name: "Which island?" })).toBeNull();
  });

  it("keeps an error after the stages that already appeared", () => {
    render(<WorkflowTurns session={{ ...session, phase: "error", answer: null, error: "The model service did not respond in time." }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("did not respond in time");
    expect(screen.queryByRole("status")).toBeNull();
    follows("Critic approved", "The model service did not respond in time.");
  });

  it("offers keyboard-accessible review recovery while keeping completed stages", async () => {
    const user = userEvent.setup();
    const retryReview = vi.fn();
    render(<WorkflowTurns session={{ ...session, phase: "error", answer: null, critique: null,
      error: "Your analysis is saved. Retry the review.", canRetryReview: true, retryReview }} />);
    const button = screen.getByRole("button", { name: "Retry review" });
    button.focus();
    await user.keyboard("{Enter}");
    expect(retryReview).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Interpretation finished" })).toBeVisible();
    expect(screen.queryByText(session.answer!.text)).toBeNull();
  });
});
