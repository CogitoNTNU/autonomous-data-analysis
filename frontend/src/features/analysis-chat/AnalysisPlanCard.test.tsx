import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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
};

describe("AnalysisPlanCard", () => {
  it("shows the objective, ordered steps, and assumptions", () => {
    render(<AnalysisPlanCard plan={plan} />);

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

  it("omits the assumptions section when none are provided", () => {
    render(
      <AnalysisPlanCard
        plan={{
          ...plan,
          assumptions: [],
        }}
      />,
    );

    expect(screen.queryByText("Assumptions")).toBeNull();
  });
});
