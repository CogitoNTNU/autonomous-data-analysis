import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PreprocessingReportCard } from "@/features/analysis-chat/PreprocessingReportCard";
import type { PreprocessingReport } from "@/types/planner";

const report: PreprocessingReport = {
  changes: ["drop_missing (handle_missing_values): Dropped 1 row"],
  affectedColumns: ["age"],
  rowsBefore: 2,
  rowsAfter: 1,
  warnings: ["One row was removed."],
};

describe("PreprocessingReportCard", () => {
  it("starts collapsed and reveals the changes when opened", async () => {
    const user = userEvent.setup();
    render(<PreprocessingReportCard report={report} />);

    expect(screen.getByText("Preprocessing")).toBeVisible();
    expect(screen.getByText("Preprocessing finished, 2 rows to 1")).toBeVisible();
    expect(screen.queryByText("2 rows in, 1 rows out.")).toBeNull();

    await user.click(
      screen.getByRole("button", { name: "Preprocessing finished, 2 rows to 1" }),
    );

    expect(screen.getByText("2 rows in, 1 rows out.")).toBeVisible();
    expect(
      screen.getByText("drop_missing (handle_missing_values): Dropped 1 row"),
    ).toBeVisible();
    expect(screen.getByText("One row was removed.")).toBeVisible();
  });

  it("says nothing changed when the plan has no preprocessing steps", async () => {
    const user = userEvent.setup();
    render(
      <PreprocessingReportCard
        report={{ ...report, changes: [], warnings: [], rowsAfter: 2 }}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Preprocessing finished, 2 rows to 2" }),
    );

    expect(screen.getByText("No rows or columns were changed.")).toBeVisible();
    expect(screen.queryByText("One row was removed.")).toBeNull();
  });
});