import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppSidebar } from "@/features/workspace/AppSidebar";

describe("AppSidebar", () => {
  it("shows an honest empty state instead of example history", () => {
    render(
      <AppSidebar
        onNewAnalysis={vi.fn()}
      />,
    );

    expect(screen.getByText("No saved analyses yet.")).toBeVisible();
    expect(screen.queryByText("Penguin body mass analysis")).toBeNull();
  });

  it("starts a new analysis from the sidebar", async () => {
    const onNewAnalysis = vi.fn();
    const user = userEvent.setup();
    render(
      <AppSidebar
        onNewAnalysis={onNewAnalysis}
      />,
    );

    await user.click(screen.getByRole("button", { name: "New analysis" }));

    expect(onNewAnalysis).toHaveBeenCalledOnce();
  });
});
