import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalysisSummaryTable } from "@/features/analysis-chat/AnalysisSummaryTable";
import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import type { AnalysisTable } from "@/types/planner";

const table: AnalysisTable = {
  id: "mass", columns: ["species", "mean_mass_g", "mean_flipper_mm"],
  rows: [["Gentoo", 5076.016, 217.187], ["Chinstrap", 3733.088, 195.824], ["Adelie", 3700.662, 189.954]],
  groupSizes: [123, 68, 151], sampleSize: 342,
};
describe("calculated summary table", () => {
  it("shows source observations separately from groups", () => {
    render(<AnalysisSummaryTable table={table} />);
    expect(screen.getByRole("table", { name: "Analysis summary table" })).toBeVisible();
    expect(screen.getByText("342 observations · 3 groups")).toBeVisible();
    expect(screen.getByRole("cell", { name: "5,076.016" })).toBeVisible();
    expect(screen.getByRole("cell", { name: "123" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Observations" })).toBeVisible();
  });
  it("shows the table immediately in the final answer", () => {
    render(<ChatAnswerCard answer={{ text: "Gentoo are largest among the three species in this dataset.", findings: [], limitations: [], figureIds: [], followUps: [] }} figures={[]} tables={[table]} />);
    expect(screen.getByRole("table", { name: "Analysis summary table" })).toBeVisible();
  });
  it("handles empty grouped results", () => {
    render(<AnalysisSummaryTable table={{ ...table, rows: [], groupSizes: [] }} />);
    expect(screen.getByText("No grouped results.")).toBeVisible();
  });
});
