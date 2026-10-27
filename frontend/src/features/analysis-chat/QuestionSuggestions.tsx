import type { DatasetPreview } from "@/types/dataset";

type QuestionSuggestionsProps = {
  dataset: DatasetPreview;
  onSelect: (question: string) => void;
};

function suggestedQuestions(columns: string[]): string[] {
  const columnNames = new Set(columns.map((column) => column.toLowerCase()));
  const isPenguinDataset =
    columnNames.has("species") &&
    columnNames.has("body_mass_g") &&
    columnNames.has("flipper_length_mm");

  if (isPenguinDataset) {
    return [
      "What is the average body mass by species?",
      "Which penguins are the largest?",
      "Is bill length related to flipper length?",
    ];
  }

  return [
    "Summarize the most important patterns",
    "Which columns contain missing values?",
    "Are any numeric columns strongly related?",
  ];
}

export function QuestionSuggestions({
  dataset,
  onSelect,
}: QuestionSuggestionsProps) {
  return (
    <section aria-label="Suggested questions" className="mb-3">
      <p className="px-1 text-sm font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        Try asking
      </p>
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {suggestedQuestions(dataset.columns).map((question) => (
          <button
            className="rounded-xl border border-border bg-background px-3 py-3 text-left text-base leading-7 text-muted-foreground shadow-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            key={question}
            onClick={() => onSelect(question)}
            type="button"
          >
            {question}
          </button>
        ))}
      </div>
    </section>
  );
}
