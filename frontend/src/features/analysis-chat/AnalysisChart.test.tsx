import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AnalysisChart } from "@/features/analysis-chat/AnalysisChart";

const figure = { id: "chart-1", image: "data:image/png;base64,chart" };

describe("AnalysisChart", () => {
  it("opens the original chart and closes it with the cross", async () => {
    const user = userEvent.setup();
    render(<AnalysisChart figure={figure} label="Analysis chart" />);
    expect(screen.queryByRole("dialog")).toBeNull();
    const trigger = screen.getByRole("button", { name: "Enlarge analysis chart" });
    expect(screen.queryByText("Click to enlarge")).toBeNull();
    await user.click(within(trigger).getByRole("img"));
    const dialog = screen.getByRole("dialog", { name: "Analysis chart" });
    expect(within(dialog).getByRole("img")).toHaveAttribute("src", figure.image);
    expect(within(dialog).getAllByRole("button")).toHaveLength(1);
    await user.click(within(dialog).getByRole("button", { name: "Close chart" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("supports opening with the keyboard and dismissing with Escape", async () => {
    const user = userEvent.setup();
    render(<AnalysisChart figure={figure} label="Analysis chart" />);
    await user.tab();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("dialog")).toBeVisible();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(screen.getByRole("button", { name: "Enlarge analysis chart" })).toHaveFocus());
  });
});
