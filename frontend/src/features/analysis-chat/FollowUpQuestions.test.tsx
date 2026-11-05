import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FollowUpQuestions } from "@/features/analysis-chat/FollowUpQuestions";

describe("FollowUpQuestions", () => {
  it("sends the chosen question with a click or the keyboard", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<FollowUpQuestions questions={["Which island?", "Why Gentoo?"]} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: "Which island?" }));
    screen.getByRole("button", { name: "Why Gentoo?" }).focus();
    await user.keyboard("{Enter}");
    expect(onSelect.mock.calls).toEqual([["Which island?"], ["Why Gentoo?"]]);
    expect(screen.getByRole("group", { name: "Follow-up questions" })).toBeVisible();
  });

  it("renders nothing without suggestions", () => {
    const { container } = render(<FollowUpQuestions questions={[]} onSelect={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("constrains a long suggestion to the available width", () => {
    const question = `Compare ${"revenue".repeat(30)} across regions`;

    render(<FollowUpQuestions questions={[question]} onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: question })).toHaveClass(
      "max-w-full",
      "min-w-0",
      "shrink",
      "whitespace-normal",
      "break-words",
    );
  });
});
