import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ImportantNotes } from "@/features/analysis-chat/ImportantNotes";

const explanation = "P-PDG, QGL, and T-PDG are constant, so correlations involving them cannot be calculated.";
const constant = "CONSTANT_COLUMN (descriptive_statistics, step stats): P-PDG constant";
const undefinedPair = "INSUFFICIENT_DATA (correlation_analysis, step corr): Correlation is undefined for P-ANULAR and P-PDG";
const partial = "Result 'result-1' is partial; its warnings must accompany any findings.";

describe("ImportantNotes", () => {
  it("shows the explanation once and keeps repeated pair diagnostics in collapsed details", async () => {
    const user = userEvent.setup();
    const pairs = Array.from({ length: 21 }, (_, index) => `INSUFFICIENT_DATA (correlation_analysis, step corr): Correlation is undefined for sensor-${index} and P-PDG`);
    render(<ImportantNotes limitations={[explanation, constant, ...pairs, partial, constant, explanation]} />);

    const section = screen.getByRole("region", { name: "Important notes" });
    expect(within(section).getAllByText(explanation)).toHaveLength(1);
    expect(screen.getByText(constant)).not.toBeVisible();
    for (const pair of pairs) expect(screen.getByText(pair)).not.toBeVisible();
    expect(screen.getByText(partial)).not.toBeVisible();

    const disclosure = screen.getByText("Technical details (23)");
    await user.tab();
    expect(disclosure).toHaveFocus();
    await user.click(disclosure);
    expect(screen.getByText(constant)).toBeVisible();
    for (const pair of pairs) expect(screen.getByText(pair)).toBeVisible();
    expect(screen.getByText(partial)).toBeVisible();
    await user.click(disclosure);
    expect(screen.getByText(constant)).not.toBeVisible();
  });

  it("summarizes diagnostics when no explanatory notes were supplied", () => {
    render(<ImportantNotes limitations={[constant, undefinedPair]} />);

    expect(screen.getByText("Some columns are constant and cannot support correlation calculations.")).toBeVisible();
    expect(screen.getByText(/Some calculations are undefined/)).toBeVisible();
    expect(screen.getByText(undefinedPair)).not.toBeVisible();
  });

  it("keeps unexpected warnings, failures, and ordinary limitations visible", () => {
    const failure = "TOOL_FAILURE (analysis, step corr): The step did not complete.";
    const unknown = "NEW_WARNING (analysis, step stats): Check the measurement scale.";
    const malformed = "INSUFFICIENT_DATA needs investigation.";
    render(<ImportantNotes limitations={[failure, unknown, malformed, "Assumption: observations are independent."]} />);

    expect(screen.getByText(failure)).toBeVisible();
    expect(screen.getByText(unknown)).toBeVisible();
    expect(screen.getByText(malformed)).toBeVisible();
    expect(screen.getByText("Assumption: observations are independent.")).toBeVisible();
    expect(screen.queryByText(/Technical details/)).toBeNull();
  });

  it("keeps missing-label qualifications visible when only diagnostics exist", () => {
    render(<ImportantNotes limitations={["MISSING_GROUP_VALUES (group_aggregate, step groups): class has 3600 missing group value(s); retained as null"]} />);

    expect(screen.getByText("Some grouping labels are missing and were retained as null groups.")).toBeVisible();
  });

  it("explains partial results even without individual warnings", () => {
    render(<ImportantNotes limitations={[partial]} />);

    expect(screen.getByText("Some analysis results are partial. See technical details for their recorded limitations.")).toBeVisible();
    expect(screen.getByText(partial)).not.toBeVisible();
  });

  it("does not create an empty notes section", () => {
    render(<ImportantNotes limitations={["", "  "]} />);

    expect(screen.queryByRole("region", { name: "Important notes" })).toBeNull();
  });
});
