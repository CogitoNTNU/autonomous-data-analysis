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
        <div className="flex min-h-20 items-center gap-2 rounded-3xl border border-border bg-composer p-2 shadow-sm transition-colors focus-within:border-ring">
          <Textarea
            aria-label="Analysis question"
            className="max-h-32 min-h-0 flex-1 resize-none border-0 bg-transparent px-4 py-3 text-base leading-7 shadow-none focus-visible:ring-0"
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
            rows={1}
            value={question}
          />
            <Button
              aria-label="Send question"
              className="shrink-0 rounded-full border border-emerald-600/40 bg-emerald-600 text-white transition-[background-color,color,border-color,transform,box-shadow] duration-200 ease-out enabled:scale-100 enabled:shadow-sm hover:bg-emerald-700 active:scale-95 disabled:scale-95 disabled:bg-emerald-600/15 disabled:text-emerald-700 disabled:opacity-100 dark:disabled:text-emerald-400"
              disabled={!canSubmit}
              size="icon"
              type="submit"
            >
              <ArrowUp className="size-4" />
            </Button>
        </div>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Review the plan before running any analysis.
        </p>
      </form>
    </div>
  );
}
