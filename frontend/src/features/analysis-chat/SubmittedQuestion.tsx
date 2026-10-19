type SubmittedQuestionProps = {
  question: string;
};

export function SubmittedQuestion({ question }: SubmittedQuestionProps) {
  return (
    <div className="mt-9" aria-live="polite">
      <div className="flex justify-end">
        <p className="max-w-[75%] rounded-3xl bg-secondary px-5 py-3 text-xs leading-5 text-secondary-foreground">
          {question}
        </p>
      </div>
      <p className="mt-3 text-right text-[9px] text-muted-foreground">
        Question captured · planner response comes in the next step
      </p>
    </div>
  );
}
