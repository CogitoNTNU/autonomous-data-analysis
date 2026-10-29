import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { WorkflowTurns } from "@/features/analysis-chat/WorkflowTurns";
import { createPrototypeAnalysisPlan } from "@/features/analysis-chat/prototype-plan";

type Session = Parameters<typeof WorkflowTurns>[0]["session"];
const session: Session = {
  busy: false, phase: "complete", error: null,
  plan: createPrototypeAnalysisPlan("Compare body mass"),
  report: { rowsBefore: 344, rowsAfter: 342, changes: ["Removed two incomplete rows."], affectedColumns: [], warnings: [] },
  analysis: null,
  interpretation: { summary: "Full internal interpretation", findings: [], limitations: [], unanswered: [], source: {} },
  critique: { decision: "approved", issues: [], requiredChanges: [], source: {} },
  answer: { text: "Gentoo have the greatest mean mass among these three species.", findings: [], limitations: ["Descriptive differences do not establish significance."], figureIds: [], followUps: [] },
};

describe("concise workflow presentation", () => {
  it("keeps the answer and caveats visible while processing details are collapsed", async () => {
    const user = userEvent.setup();
    render(<WorkflowTurns session={session} />);
    expect(screen.getByText(session.answer!.text)).toBeVisible();
    expect(screen.getByText(session.answer!.limitations[0])).toBeVisible();
    expect(screen.queryByText("Planner")).toBeNull();
    expect(screen.queryByText("Full internal interpretation")).toBeNull();
    const details = screen.getByRole("button", { name: "View analysis details" });
    expect(details).toHaveAttribute("aria-expanded", "false");
    details.focus();
    await user.keyboard("{Enter}");
    expect(details).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Planner")).toBeVisible();
    expect(screen.getByText("PL")).toBeVisible();
    expect(screen.getByText("PR")).toBeVisible();
    expect(screen.getByText("IN")).toBeVisible();
    expect(screen.getByText("CR")).toBeVisible();
    expect(screen.queryByText("Behind the answer")).toBeNull();
    expect(screen.getByText("Interpretation finished")).toBeVisible();
    await user.keyboard("{Enter}");
    expect(screen.queryByText("Planner")).toBeNull();
    expect(screen.getByText(session.answer!.text)).toBeVisible();
  });

  it("expands an agent card with the keyboard and preserves the main answer", async () => {
    const user = userEvent.setup();
    render(<WorkflowTurns session={session} />);
    await user.click(screen.getByRole("button", { name: "View analysis details" }));
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

  it.each(["thinking", "analysis", "critic"] as const)("shows one progress indicator during %s", (phase) => {
    render(<WorkflowTurns session={{ ...session, busy: true, phase, answer: null }} />);
    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(screen.getByRole("status", { name: "Analyzing data…" })).toBeVisible();
    expect(screen.queryByText("Planner")).toBeNull();
  });

  it("keeps errors visible without requiring the details section", () => {
    render(<WorkflowTurns session={{ ...session, phase: "error", answer: null, error: "The model service did not respond in time." }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("did not respond in time");
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByRole("button", { name: "View analysis details" })).toHaveAttribute("aria-expanded", "false");
  });
});
