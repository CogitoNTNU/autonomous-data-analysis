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
    <div className="ml-12 mt-5">
      <p className="text-xs font-medium">
        What would you like to learn from this dataset?
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {suggestedQuestions(dataset.columns).map((question) => (
          <button
            className="rounded-xl border border-border bg-background px-3 py-2 text-left text-[10px] leading-4 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            key={question}
            onClick={() => onSelect(question)}
            type="button"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
