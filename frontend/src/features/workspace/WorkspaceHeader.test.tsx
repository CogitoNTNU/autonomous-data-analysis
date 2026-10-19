import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceHeader } from "@/features/workspace/WorkspaceHeader";

describe("WorkspaceHeader", () => {
  it("requests dark mode from the light theme", async () => {
    const onToggleTheme = vi.fn();
    const user = userEvent.setup();
    render(
      <WorkspaceHeader
        hasDataset={false}
        onNewAnalysis={vi.fn()}
        onToggleTheme={onToggleTheme}
        theme="light"
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Switch to dark mode" }),
    );

    expect(onToggleTheme).toHaveBeenCalledOnce();
  });

  it("offers light mode when the dark theme is active", () => {
    render(
      <WorkspaceHeader
        hasDataset={false}
        onNewAnalysis={vi.fn()}
        onToggleTheme={vi.fn()}
        theme="dark"
      />,
    );

    expect(
      screen.getByRole("button", { name: "Switch to light mode" }),
    ).toBeVisible();
  });

  it("offers a new analysis action when a dataset is loaded", async () => {
    const onNewAnalysis = vi.fn();
    const user = userEvent.setup();
    render(
      <WorkspaceHeader
        hasDataset
        onNewAnalysis={onNewAnalysis}
        onToggleTheme={vi.fn()}
        theme="light"
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Start new analysis" }),
    );

    expect(onNewAnalysis).toHaveBeenCalledOnce();
  });
});
