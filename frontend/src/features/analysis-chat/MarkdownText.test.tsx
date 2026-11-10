import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { MarkdownText } from "@/features/analysis-chat/MarkdownText";

describe("MarkdownText", () => {
  it("renders formatted paragraphs, headings, lists, links and code", () => {
    render(<MarkdownText text={'## Limitations\n\nThe **main** concern is *missing data*.\n\n- Excluded `unit_price`\n- See [details](https://example.com/details)\n\n1. Review inputs\n2. Repeat analysis\n\n```text\nrevenue,profit\n10,2\n```'} />);

    expect(screen.getByRole("heading", { name: "Limitations" })).toBeVisible();
    expect(screen.getByText("main").tagName).toBe("STRONG");
    expect(screen.getByText("missing data").tagName).toBe("EM");
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByText("unit_price").tagName).toBe("CODE");
    expect(screen.getByRole("link", { name: "details" })).toHaveAttribute("href", "https://example.com/details");
    expect(screen.getByText(/revenue,profit/).closest("pre")).not.toBeNull();
  });

  it("renders GFM tables in a keyboard-accessible scrolling container", async () => {
    const user = userEvent.setup();
    render(<MarkdownText text={'| Region | Revenue |\n| --- | ---: |\n| East | 100 |\n| West | 90 |'} />);

    const region = screen.getByRole("region", { name: "Scrollable table" });
    expect(region).toHaveClass("overflow-x-auto", "max-w-full");
    expect(within(region).getByRole("columnheader", { name: "Revenue" })).toBeVisible();
    expect(within(region).getByRole("cell", { name: "East" })).toBeVisible();
    await user.tab();
    expect(region).toHaveFocus();
  });

  it("does not render raw HTML, executable links or remote images", () => {
    const { container } = render(<MarkdownText text={'Safe text.\n\n[unsafe](javascript:alert%281%29)\n\n![remote](https://example.com/tracker.png)\n\n<script>alert(1)</script>\n\n<img src="x" onerror="alert(1)">'} />);

    expect(screen.getByText("Safe text.")).toBeVisible();
    expect(container.querySelector("script, img")).toBeNull();
    expect(container.querySelector("a")?.getAttribute("href") ?? "").not.toMatch(/^javascript:/i);
    expect(container.querySelector("[onerror]")).toBeNull();
  });

  it("keeps incomplete Markdown readable", () => {
    render(<MarkdownText text="An **unfinished emphasis and a literal unit_price column." />);

    expect(screen.getByText("An **unfinished emphasis and a literal unit_price column.")).toBeVisible();
  });

  it("handles empty text without adding a paragraph", () => {
    const { container } = render(<MarkdownText text="" />);

    expect(container.querySelector(".markdown-body")).toBeEmptyDOMElement();
  });
});
