import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";

describe("ThinkingIndicator", () => {
  it("announces the planner progress as a status", () => {
    render(<ThinkingIndicator />);

    const status = screen.getByRole("status");
    expect(screen.getByText("Planner")).toBeVisible();
    expect(status).toHaveTextContent("Thinking");
    expect(status).toHaveTextContent("Reviewing the dataset structure");
    expect(status).toHaveTextContent(
      "Checking whether clarification is needed",
    );
  });
});
