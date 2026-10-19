import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DatasetUpload } from "@/features/dataset-upload/DatasetUpload";

describe("DatasetUpload", () => {
  it("shows the initial CSV upload prompt", () => {
    render(<DatasetUpload />);

    expect(
      screen.getByRole("heading", { name: "What are you analyzing?" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose file" })).toBeEnabled();
  });

  it("shows a validation error for a non-CSV file", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<DatasetUpload />);

    const file = new File(["not,a,dataset"], "notes.txt", {
      type: "text/plain",
    });
    await user.upload(screen.getByLabelText("Choose CSV file"), file);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose a CSV file to continue.",
    );
  });

  it("accepts an uppercase CSV extension and presents the selected file", async () => {
    const user = userEvent.setup();
    render(<DatasetUpload />);

    const file = new File(["species,mass\nAdelie,3700"], "PENGUINS.CSV", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText("Choose CSV file"), file);

    expect(await screen.findByText("CSV selected")).toBeInTheDocument();
    expect(screen.getByText("PENGUINS.CSV")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Choose another file" }),
    ).toBeEnabled();
  });
});
