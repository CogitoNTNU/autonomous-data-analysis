import { Button } from "@/components/ui/button";
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
      <p className="px-1 text-sm font-medium leading-5 text-muted-foreground">
        Try asking
      </p>
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {suggestedQuestions(dataset.columns).map((question) => (
          <Button
            variant="outline"
            className="h-auto min-h-20 items-start justify-start whitespace-normal rounded-xl px-3 py-3 text-left text-base font-normal leading-7 text-foreground shadow-sm hover:bg-muted"
            key={question}
            onClick={() => onSelect(question)}
            type="button"
          >
            {question}
          </Button>
        ))}
      </div>
    </section>
  );
}
