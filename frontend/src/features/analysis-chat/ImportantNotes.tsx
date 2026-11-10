import { importantNotes } from "@/features/analysis-chat/important-notes";
import { TextList } from "@/features/analysis-chat/TextList";

export function ImportantNotes({ limitations }: { limitations: string[] }) {
  const { notes, details } = importantNotes(limitations);
  if (notes.length === 0 && details.length === 0) return null;

  return (
    <section aria-label="Important notes">
      <TextList items={notes} title="Important notes" />
      {details.length > 0 && (
        <details className="mt-3 text-sm text-muted-foreground">
          <summary className="cursor-pointer hover:text-foreground">
            Technical details ({details.length})
          </summary>
          <TextList items={details} title="Recorded warnings and result status" />
        </details>
      )}
    </section>
  );
}
