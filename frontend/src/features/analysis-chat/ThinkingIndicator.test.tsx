import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { agents } from "@/features/analysis-chat/agents";
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

  it("shows one readable DAP status without repeating its label", () => {
    render(<ThinkingIndicator agent={agents.assistant} label="Analyzing data…" />);

    expect(screen.getByText("Data Analysis Planner", { selector: "p" })).toBeVisible();
    expect(screen.getByText("DAP")).toBeVisible();
    expect(screen.getByRole("status")).toHaveAccessibleName("Analyzing data…");
    expect(screen.getAllByText("Analyzing data…")).toHaveLength(1);
    expect(screen.getByRole("status").querySelectorAll(".thinking-dot")).toHaveLength(3);
  });

});
