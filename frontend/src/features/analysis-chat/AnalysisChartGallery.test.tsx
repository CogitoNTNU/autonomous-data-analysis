import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { AnalysisChartGallery } from "@/features/analysis-chat/AnalysisChartGallery";

const figures = [
  { id: "distribution", image: "data:image/png;base64,distribution" },
  { id: "average", image: "data:image/png;base64,average" },
];

describe("AnalysisChartGallery", () => {
  it("groups plots in the requested order and opens the selected original", async () => {
    const user = userEvent.setup();
    render(<AnalysisChartGallery figures={figures} figureIds={["average", "distribution", "average"]} />);
    const gallery = screen.getByRole("group", { name: "Analysis charts" });
    const previews = within(gallery).getAllByRole("img");
    expect(previews).toHaveLength(2);
    expect(previews[0]).toHaveAttribute("src", figures[1].image);
    await user.click(within(gallery).getByRole("button", { name: "Enlarge analysis chart 2" }));
    const dialog = screen.getByRole("dialog", { name: "Analysis chart 2" });
    expect(within(dialog).getByRole("img")).toHaveAttribute("src", figures[0].image);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows an explicit message for missing or empty chart images", () => {
    render(<AnalysisChartGallery figures={[{ id: "empty", image: " " }]} figureIds={["missing", "empty"]} />);
    expect(screen.getAllByText("This chart could not be loaded")).toHaveLength(2);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("omits the gallery when no charts are referenced", () => {
    render(<AnalysisChartGallery figures={figures} figureIds={[]} />);
    expect(screen.queryByRole("group", { name: "Analysis charts" })).toBeNull();
  });
});
