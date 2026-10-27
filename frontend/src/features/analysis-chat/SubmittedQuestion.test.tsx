import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SubmittedQuestion } from "@/features/analysis-chat/SubmittedQuestion";

describe("SubmittedQuestion", () => {
  it("copies the sent message", async () => {
    const user = userEvent.setup();
    render(<SubmittedQuestion question="Compare species" onEdit={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Copy message" }));
    expect(await navigator.clipboard.readText()).toBe("Compare species");
    expect(screen.getByText("Copied to clipboard")).toBeVisible();
  });

  it("shows a copy failure", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("Denied"));
    render(<SubmittedQuestion question="Compare species" onEdit={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Copy message" }));
    expect(screen.getByText("Could not copy the message")).toBeVisible();
  });

  it("edits the message using the keyboard", async () => {
    const user = userEvent.setup();
    const edit = vi.fn();
    render(<SubmittedQuestion question="Compare species" onEdit={edit} />);
    screen.getByRole("button", { name: "Edit message" }).focus();
    await user.keyboard("{Enter}");
    expect(edit).toHaveBeenCalledWith("Compare species");
  });

  it("disables editing while the workflow runs", () => {
    render(<SubmittedQuestion question="Compare species" onEdit={vi.fn()} editDisabled />);
    expect(screen.getByRole("button", { name: "Edit message" })).toBeDisabled();
  });
});
