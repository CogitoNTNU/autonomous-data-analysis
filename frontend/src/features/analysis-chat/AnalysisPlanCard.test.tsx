import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import type { AnalysisPlan } from "@/types/planner";

const plan: AnalysisPlan = {
  id: "plan-1",
  objective: "Compare sales by city",
  status: "draft",
  steps: [
    {
      id: "step-1",
      title: "Group sales",
      description: "Calculate totals for each city.",
    },
  ],
  assumptions: ["The amount column contains sales values."],
  source: {
    plan_id: "plan-1",
    objective: "Compare sales by city",
    required_columns: ["city", "amount"],
    preprocessing_steps: [],
    analysis_steps: [],
    expected_outputs: [],
    assumptions: ["The amount column contains sales values."],
  },
};

describe("AnalysisPlanCard", () => {
  it("starts collapsed and reveals the whole plan when opened", async () => {
    const user = userEvent.setup();
    render(<AnalysisPlanCard plan={plan} />);

    expect(screen.queryByText("Compare sales by city")).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Prepared an analysis plan, 1 step" }),
    );

    expect(
      screen.getByRole("heading", { name: "Analysis plan" }),
    ).toBeVisible();
    expect(screen.getByText("Compare sales by city")).toBeVisible();
    expect(screen.getByRole("list", { name: "Plan steps" })).toBeVisible();
    expect(screen.getByText("Group sales")).toBeVisible();
    expect(
      screen.getByText("The amount column contains sales values."),
    ).toBeVisible();
  });

  it("hides the plan again when the summary is pressed", async () => {
    const user = userEvent.setup();
    render(<AnalysisPlanCard plan={plan} />);
    const summary = screen.getByRole("button", {
      name: "Prepared an analysis plan, 1 step",
    });

    await user.click(summary);
    await user.click(summary);

    expect(screen.queryByText("Compare sales by city")).toBeNull();
    expect(summary).toHaveAttribute("aria-expanded", "false");
  });

  it("omits the assumptions section when none are provided", async () => {
    const user = userEvent.setup();
    render(<AnalysisPlanCard plan={{ ...plan, assumptions: [] }} />);

    await user.click(
      screen.getByRole("button", { name: "Prepared an analysis plan, 1 step" }),
    );

    expect(screen.queryByText("Assumptions")).toBeNull();
  });

  it("shows continue while the plan stays collapsed", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<AnalysisPlanCard onRun={onRun} plan={plan} />);

    expect(screen.queryByText("Compare sales by city")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(onRun).toHaveBeenCalledOnce();
    expect(screen.queryByText("Compare sales by city")).toBeNull();
  });
});
