import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { prototypePlanner } from "@/features/analysis-chat/prototype-planner";

describe("App dataset preview flow", () => {
  it("closes and reopens the sidebar", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);
    await user.click(screen.getByRole("button", { name: "Close sidebar" }));
    expect(document.getElementById("workspace-sidebar")).toHaveClass("w-0", "opacity-0");
    expect(document.getElementById("workspace-sidebar")).toHaveAttribute("inert");
    await user.click(screen.getByRole("button", { name: "Open sidebar" }));
    expect(document.getElementById("workspace-sidebar")).toHaveClass("w-[260px]", "opacity-100");
    expect(document.getElementById("workspace-sidebar")).not.toHaveAttribute("inert");
  });

  it("switches between light and dark mode", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    await user.click(
      screen.getByRole("button", { name: "Switch to dark mode" }),
    );

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("data-analysis-theme")).toBe("dark");

    await user.click(
      screen.getByRole("button", { name: "Switch to light mode" }),
    );

    expect(document.documentElement).not.toHaveClass("dark");
  });

  it("shows a table preview after a valid CSV is selected", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    expect(screen.queryByRole("region", { name: "Suggested questions" })).toBeNull();

    const file = new File(
      ["species,island,body_mass_g\nAdelie,Torgersen,3750\nGentoo,Biscoe,5000"],
      "penguins.csv",
      { type: "text/csv" },
    );
    await user.upload(screen.getByLabelText("Choose CSV file"), file);

    expect(
      await screen.findByText(/It contains 2 rows and 3 columns/),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "species" })).toBeVisible();
    expect(screen.getByRole("cell", { name: "Gentoo" })).toBeVisible();
  });

  it("returns to the upload screen when the dataset is replaced", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    const file = new File(["name,value\nAda,1"], "sample.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await user.click(await screen.findByRole("button", { name: "Replace file" }));

    expect(
      screen.getByRole("heading", { name: "What are you analyzing?" }),
    ).toBeVisible();
  });

  it("submits a suggested analysis question after loading a dataset", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    const file = new File(
      [
        "species,bill_length_mm,flipper_length_mm,body_mass_g\nAdelie,39.1,181,3750",
      ],
      "penguins.csv",
      { type: "text/csv" },
    );
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    const suggestion = await screen.findByRole("button", {
      name: "What is the average body mass by species?",
    });
    const bar = screen.getByRole("region", { name: "Suggested questions" });
    const composer = screen.getByRole("form", { name: "Ask about the dataset" });
    expect(bar.parentElement?.parentElement).toBe(composer.parentElement);
    expect(bar.compareDocumentPosition(composer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    suggestion.focus();
    await user.keyboard("{Enter}");
    expect(screen.queryByRole("region", { name: "Suggested questions" })).toBeNull();

    expect(
      screen.getByText("What is the average body mass by species?", { selector: "p" }),
    ).toBeVisible();
    expect(screen.getByRole("status", { name: "Thinking" })).toBeVisible();
    expect(screen.getByLabelText("Analysis question")).toBeDisabled();
    await user.click(
      await screen.findByRole("button", {
        name: "Prepared an analysis plan, 3 steps",
      }),
    );
    expect(
      screen.getByRole("heading", { name: "Analysis plan" }),
    ).toBeVisible();
  });

  it("asks for clarification when more than one size measure is available", async () => {
    const user = userEvent.setup();
    render(<App planner={prototypePlanner} />);

    const file = new File(
      [
        "species,body_mass_g,flipper_length_mm\nAdelie,3750,181\nGentoo,5000,215",
      ],
      "penguins.csv",
      { type: "text/csv" },
    );
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await user.click(
      await screen.findByRole("button", {
        name: "Which penguins are the largest?",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "What do you mean by “largest”?",
      }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Body mass" }));

    expect(screen.getByText("Body mass")).toBeVisible();
    expect(screen.getByRole("status", { name: "Thinking" })).toBeVisible();
    expect(
      await screen.findByRole("button", {
        name: "Prepared an analysis plan, 3 steps",
      }),
    ).toBeVisible();
  });

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
      screen.getByRole("region", { name: "Suggested questions" }),
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
    await user.click(screen.getByRole("button", { name: "Prepare dataset" }));

    for (const label of ["Run analysis", "Interpret results", "Review findings", "Show final answer"]) {
      expect(screen.queryByRole("button", { name: "Prepared an answer" })).toBeNull();
      await user.click(await screen.findByRole("button", { name: label }));
    }

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
    await user.click(screen.getByRole("button", { name: "Prepared an answer" }));
    expect(screen.getByText("The prepared columns can be compared.")).toBeVisible();
  });
});
