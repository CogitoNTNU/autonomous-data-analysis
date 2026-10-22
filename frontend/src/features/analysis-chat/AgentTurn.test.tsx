import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";

describe("AgentTurn", () => {
  it("shows the speaking agent's name and initials", () => {
    const view = render(
      <AgentTurn agent={agents.planner}>
        <p>Which column should be used?</p>
      </AgentTurn>,
    );

    expect(screen.getByText("Planner")).toBeVisible();
    expect(view.container).toHaveTextContent("PL");
    expect(screen.getByText("Which column should be used?")).toBeVisible();
  });
});
