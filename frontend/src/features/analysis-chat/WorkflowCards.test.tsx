import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CriticCard } from "@/features/analysis-chat/WorkflowCards";

describe("critic approval badge", () => {
  it.each(["approved", "revise", "cannot_complete"] as const)(
    "shows approval only for an approved review (%s)",
    (decision) => {
      render(<CriticCard critique={{ decision, issues: [], requiredChanges: [], source: {} }} />);
      if (decision === "approved") {
        expect(screen.getByText("Approved", { exact: true })).toBeVisible();
      } else {
        expect(screen.queryByText("Approved", { exact: true })).toBeNull();
      }
    },
  );
});
