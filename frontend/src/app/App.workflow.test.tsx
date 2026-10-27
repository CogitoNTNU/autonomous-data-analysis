import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { prototypePlanner } from "@/features/analysis-chat/prototype-planner";

describe("App prepared plan flow", () => {
  it("starts a new question without discarding the loaded dataset", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    const file = new File(["city,amount\nOslo,249\nBergen,1299"], "sales.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await user.click(
      await screen.findByRole("button", {
        name: "Summarize the most important patterns",
      }),
    );
    expect(
      await screen.findByRole("button", {
        name: "Prepared an analysis plan, 3 steps",
      }),
    ).toBeVisible();

    await user.click(
      screen.getByRole("button", { name: "Start new analysis" }),
    );

    expect(
      screen.getByText("What would you like to learn from this dataset?"),
    ).toBeVisible();
    expect(screen.getByLabelText("Analysis question")).toBeEnabled();
    expect(
      screen.queryByRole("button", {
        name: "Prepared an analysis plan, 3 steps",
      }),
    ).toBeNull();
    expect(screen.getByRole("columnheader", { name: "city" })).toBeVisible();
  });

  it("runs preprocessing after the plan is reviewed", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    const file = new File(["city,amount\nOslo,249\nBergen,1299"], "sales.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await user.click(
      await screen.findByRole("button", {
        name: "Summarize the most important patterns",
      }),
    );
    expect(
      await screen.findByRole("button", { name: "Prepared an analysis plan, 3 steps" }),
    ).toBeVisible();
    expect(screen.queryByText(/The uploaded CSV is the dataset/)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      await screen.findByRole("button", { name: "Prepared an answer" }),
    ).toBeVisible();
    expect(screen.getByText("Preprocessing finished, 2 rows to 2")).toBeVisible();
    expect(screen.getByText("Analysis finished, 1 result")).toBeVisible();
    expect(screen.getByText("Interpretation finished")).toBeVisible();
    expect(screen.getByText("Critic approved")).toBeVisible();
    expect(
      screen.queryByText(
        "prepare (select_columns): Kept the columns used by the question.",
      ),
    ).toBeNull();

    await user.click(
      screen.getByRole("button", { name: "Preprocessing finished, 2 rows to 2" }),
    );
    expect(
      screen.getByText(
        "prepare (select_columns): Kept the columns used by the question.",
      ),
    ).toBeVisible();
    expect(screen.getByText("The prepared columns can be compared.")).toBeVisible();
  });
});
