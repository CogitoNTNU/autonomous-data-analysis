import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";

describe("App dataset preview flow", () => {
  it("shows a table preview after a valid CSV is selected", async () => {
    const user = userEvent.setup();
    render(<App />);

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
    render(<App />);

    const file = new File(["name,value\nAda,1"], "sample.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await user.click(
      await screen.findByRole("button", { name: "Replace dataset" }),
    );

    expect(
      screen.getByRole("heading", { name: "What are you analyzing?" }),
    ).toBeVisible();
  });

  it("submits a suggested analysis question after loading a dataset", async () => {
    const user = userEvent.setup();
    render(<App />);

    const file = new File(
      [
        "species,bill_length_mm,flipper_length_mm,body_mass_g\nAdelie,39.1,181,3750",
      ],
      "penguins.csv",
      { type: "text/csv" },
    );
    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await user.click(
      await screen.findByRole("button", {
        name: "What is the average body mass by species?",
      }),
    );

    expect(
      screen.getByText("What is the average body mass by species?"),
    ).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Thinking");
    expect(screen.getByLabelText("Analysis question")).toBeDisabled();
    expect(
      await screen.findByRole("heading", { name: "Analysis plan" }),
    ).toBeVisible();
  });

  it("asks for clarification when more than one size measure is available", async () => {
    const user = userEvent.setup();
    render(<App />);

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
    expect(screen.getByRole("status")).toHaveTextContent("Thinking");
    expect(
      await screen.findByRole("heading", { name: "Analysis plan" }),
    ).toBeVisible();
  });
});
