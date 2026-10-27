import { LoaderCircle, RefreshCw } from "lucide-react";
import { useRef, useState } from "react";

import { readCsvPreview } from "@/features/dataset-upload/read-csv-preview";
import { validateDatasetFile } from "@/features/dataset-upload/validate-dataset-file";
import type { DatasetPreview } from "@/types/dataset";

type DatasetReplaceButtonProps = {
  onReplace: (preview: DatasetPreview, file: File) => Promise<boolean>;
};

export function DatasetReplaceButton({ onReplace }: DatasetReplaceButtonProps) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function replace(file: File) {
    setError(null);
    setBusy(true);
    try {
      const invalid = validateDatasetFile(file);
      if (invalid) throw new Error(invalid);
      const preview = await readCsvPreview(file);
      if (!(await onReplace(preview, file))) {
        throw new Error("The new dataset could not be registered. Please try again.");
      }
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "The CSV could not be read.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative shrink-0">
      <input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        aria-label="Replace CSV file"
        className="hidden"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.item(0);
          if (file) void replace(file);
          event.target.value = "";
        }}
      />
      <button
        type="button"
        aria-label="Replace dataset"
        title="Replace dataset"
        disabled={busy}
        onClick={() => input.current?.click()}
        className="grid size-8 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
      >
        {busy ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : <RefreshCw aria-hidden="true" className="size-4" />}
      </button>
      {busy && <span role="status" className="sr-only">Loading CSV…</span>}
      {error && <p role="alert" className="absolute right-0 top-full z-20 mt-2 w-64 rounded-lg border border-border bg-background p-3 text-sm text-destructive shadow-lg">{error}</p>}

    </div>
  );
}
