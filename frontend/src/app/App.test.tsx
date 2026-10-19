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
});
