import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AnalysisQuestionComposer } from "@/features/analysis-chat/AnalysisQuestionComposer";

describe("AnalysisQuestionComposer", () => {
  it("keeps submission disabled until a dataset and question are available", () => {
    render(
      <AnalysisQuestionComposer
        disabled={false}
        hasDataset={false}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        question=""
      />,
    );

    expect(screen.getByLabelText("Analysis question")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send question" })).toBeDisabled();
  });

  it("submits a trimmed question when Enter is pressed", async () => {
    const onChange = vi.fn();
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <AnalysisQuestionComposer
        disabled={false}
        hasDataset
        onChange={onChange}
        onSubmit={onSubmit}
        question=""
      />,
    );

    await user.type(screen.getByLabelText("Analysis question"), " average mass ");
    expect(onChange).toHaveBeenCalled();

    rerender(
      <AnalysisQuestionComposer
        disabled={false}
        hasDataset
        onChange={onChange}
        onSubmit={onSubmit}
        question=" average mass "
      />,
    );
    await user.type(screen.getByLabelText("Analysis question"), "{Enter}");

    expect(onSubmit).toHaveBeenCalledWith("average mass");
  });
});
