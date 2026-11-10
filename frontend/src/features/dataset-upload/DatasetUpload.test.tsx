import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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

  it("keeps loading until the dataset has been registered", async () => {
    const user = userEvent.setup();
    let finish!: (registered: boolean) => void;
    const onDatasetReady = vi.fn(() => new Promise<boolean>((resolve) => { finish = resolve; }));
    render(<DatasetUpload onDatasetReady={onDatasetReady} />);
    const file = new File(["name,value\nAda,1"], "sample.csv", { type: "text/csv" });

    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await waitFor(() => expect(onDatasetReady).toHaveBeenCalledOnce());

    expect(screen.getByText("Loading CSV")).toBeVisible();
    expect(screen.getByLabelText("Choose CSV file")).toBeDisabled();
    expect(screen.queryByText("CSV selected")).toBeNull();
    await act(async () => finish(true));
    expect(await screen.findByText("CSV selected")).toBeVisible();
  });

  it("allows the same file to be retried after registration fails", async () => {
    const user = userEvent.setup();
    const onDatasetReady = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<DatasetUpload onDatasetReady={onDatasetReady} />);
    const file = new File(["name,value\nAda,1"], "sample.csv", { type: "text/csv" });

    await user.upload(screen.getByLabelText("Choose CSV file"), file);
    await waitFor(() => expect(onDatasetReady).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByRole("button", { name: "Choose file" })).toBeEnabled());
    expect(screen.queryByText("CSV selected")).toBeNull();
    await user.upload(screen.getByLabelText("Choose CSV file"), file);

    expect(await screen.findByText("CSV selected")).toBeVisible();
    expect(onDatasetReady).toHaveBeenCalledTimes(2);
  });

  it("shows registration errors without claiming the CSV was selected", async () => {
    const user = userEvent.setup();
    const onDatasetReady = vi.fn().mockRejectedValue(new Error("Dataset storage is unavailable"));
    render(<DatasetUpload onDatasetReady={onDatasetReady} />);

    await user.upload(screen.getByLabelText("Choose CSV file"), new File(["name\nAda"], "sample.csv", { type: "text/csv" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Dataset storage is unavailable");
    expect(screen.queryByText("CSV selected")).toBeNull();
    expect(screen.getByRole("button", { name: "Choose file" })).toBeEnabled();
  });
});
