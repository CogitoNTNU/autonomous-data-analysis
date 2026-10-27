import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";

describe("ThinkingIndicator", () => {
  it("announces the planner progress as a status", () => {
    render(<ThinkingIndicator />);

    const status = screen.getByRole("status");
    expect(screen.getByText("Planner")).toBeVisible();
    expect(status).toHaveAccessibleName("Thinking");
    expect(screen.queryByText("Thinking")).toBeNull();
    expect(status.querySelectorAll(".thinking-dot")).toHaveLength(3);
  });
});
