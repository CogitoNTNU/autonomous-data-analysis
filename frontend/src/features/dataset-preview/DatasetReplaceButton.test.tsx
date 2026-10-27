import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DatasetReplaceButton } from "@/features/dataset-preview/DatasetReplaceButton";

const csv = new File(["name,value\nAda,1"], "new.csv", { type: "text/csv" });

describe("DatasetReplaceButton", () => {
  it("opens the dataset actions with the keyboard and registers a replacement", async () => {
    const user = userEvent.setup();
    const replace = vi.fn().mockResolvedValue(true);
    render(<DatasetReplaceButton onReplace={replace} />);
    await user.tab();
    await user.keyboard("{Enter}");
    await user.upload(screen.getByLabelText("Replace CSV file"), csv);
    expect(replace).toHaveBeenCalledWith(expect.objectContaining({ fileName: "new.csv", rowCount: 1 }), csv);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the current dataset when registration fails", async () => {
    const user = userEvent.setup();
    render(<DatasetReplaceButton onReplace={async () => false} />);
    await user.upload(screen.getByLabelText("Replace CSV file"), csv);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be registered");
  });

  it("rejects an empty CSV before registration", async () => {
    const user = userEvent.setup();
    const replace = vi.fn();
    render(<DatasetReplaceButton onReplace={replace} />);
    await user.upload(screen.getByLabelText("Replace CSV file"), new File([], "empty.csv", { type: "text/csv" }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(replace).not.toHaveBeenCalled();
  });
});
