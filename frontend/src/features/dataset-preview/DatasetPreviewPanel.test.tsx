import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DatasetPreviewPanel } from "@/features/dataset-preview/DatasetPreviewPanel";
import type { DatasetPreview } from "@/types/dataset";

const dataset: DatasetPreview = {
  fileName: "penguins.csv", fileSize: 15000, rowCount: 344, columnCount: 2,
  columns: ["species", "body_mass_g"], rows: [["Adelie", "3750"], ["Gentoo", "5000"]],
};

describe("inline dataset preview", () => {
  it("shows the file card and sample rows immediately", () => {
    render(<DatasetPreviewPanel dataset={dataset} onReplaceDataset={vi.fn()} />);
    expect(screen.getByRole("columnheader", { name: "species" })).toBeVisible();
    expect(screen.getByRole("cell", { name: "Gentoo" })).toBeVisible();
    expect(screen.getByText(/It contains 344 rows and 2 columns/)).toBeVisible();
    expect(screen.getByText("Showing the first 2 of 344 rows.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Replace dataset" })).toBeVisible();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows an explicit empty state for headers-only CSVs", () => {
    render(<DatasetPreviewPanel dataset={{ ...dataset, rowCount: 0, rows: [] }} onReplaceDataset={vi.fn()} />);
    expect(screen.getByText("This CSV has column headers but no data rows.")).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("preserves the current file and rows when replacement fails", async () => {
    const user = userEvent.setup();
    render(<DatasetPreviewPanel dataset={dataset} onReplaceDataset={async () => false} />);
    await user.upload(screen.getByLabelText("Replace CSV file"), new File(["city,value\nOslo,1"], "new.csv", { type: "text/csv" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be registered");
    expect(screen.getByRole("cell", { name: "Gentoo" })).toBeVisible();
  });
});
