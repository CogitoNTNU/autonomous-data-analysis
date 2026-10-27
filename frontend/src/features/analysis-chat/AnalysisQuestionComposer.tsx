import { ArrowUp } from "lucide-react";
import type { FormEvent, KeyboardEvent, ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type AnalysisQuestionComposerProps = {
  disabled: boolean;
  finished?: boolean;
  hasDataset: boolean;
  onChange: (question: string) => void;
  onSubmit: (question: string) => void;
  question: string;
  suggestions?: ReactNode;
};

export function AnalysisQuestionComposer({
  disabled,
  finished = false,
  hasDataset,
  onChange,
  onSubmit,
  question,
  suggestions,
}: AnalysisQuestionComposerProps) {
  const canSubmit = hasDataset && !disabled && question.trim().length > 0;

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      onSubmit(question.trim());
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="composer-fade shrink-0 px-4 pb-4 pt-3 sm:px-16">
      <div className="mx-auto max-w-[800px]">{suggestions}</div>
      <form
        aria-label="Ask about the dataset"
        className="pointer-events-auto mx-auto max-w-[800px]"
        onSubmit={submitQuestion}
      >
        <div className="rounded-2xl border border-border bg-background p-2 shadow-[0_6px_24px_rgba(0,0,0,0.09)] focus-within:border-ring">
          <Textarea
            aria-label="Analysis question"
            className="max-h-32 min-h-11 resize-none border-0 px-3 py-2 text-base leading-7 shadow-none focus-visible:ring-0"
            disabled={!hasDataset || disabled}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDataset
                ? disabled
                  ? finished
                    ? "Analysis finished"
                    : "Question received"
                  : "What would you like to learn from the dataset?"
                : "Upload a CSV to start"
            }
            rows={2}
            value={question}
          />
          <div className="flex items-center">
            <span className="ml-1 text-[9px] text-muted-foreground">
              Planning only · no calculations
            </span>
            <Button
              aria-label="Send question"
              className="ml-auto"
              disabled={!canSubmit}
              size="icon"
              type="submit"
            >
              <ArrowUp className="size-4" />
            </Button>
          </div>
        </div>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Review the plan before running any analysis.
        </p>
      </form>
    </div>
  );
}
