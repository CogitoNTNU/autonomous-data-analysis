import { useRef, useState, type DragEvent } from "react";
import {
  CheckCircle2,
  FileSpreadsheet,
  LoaderCircle,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { readCsvPreview } from "@/features/dataset-upload/read-csv-preview";
import { cn } from "@/lib/utils";
import type { DatasetPreview } from "@/types/dataset";
import {
  formatFileSize,
  validateDatasetFile,
} from "@/features/dataset-upload/validate-dataset-file";

type DatasetUploadProps = {
  onDatasetReady?: (dataset: DatasetPreview, file: File) => void;
};

export function DatasetUpload({ onDatasetReady }: DatasetUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isReading, setIsReading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function selectFile(file: File) {
    const validationError = validateDatasetFile(file);

    if (validationError) {
      setSelectedFile(null);
      setError(validationError);
      return;
    }

    setError(null);
    setIsReading(true);

    try {
      const dataset = await readCsvPreview(file);
      setSelectedFile(file);
      onDatasetReady?.(dataset, file);
    } catch (reason: unknown) {
      setSelectedFile(null);
      setError(
        reason instanceof Error ? reason.message : "The CSV could not be read.",
      );
    } finally {
      setIsReading(false);
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files.item(0);
    if (file) {
      void selectFile(file);
    }
  }

  return (
    <section aria-labelledby="upload-title" className="pt-12 sm:pt-16">
      <div className="grid size-8 place-items-center rounded-full bg-foreground text-[11px] font-semibold text-background">
        DA
      </div>
      <h1
        className="mt-5 text-2xl font-semibold tracking-[-0.03em] sm:text-[26px]"
        id="upload-title"
      >
        What are you analyzing?
      </h1>
      <p className="mt-2 max-w-2xl text-base leading-7 text-muted-foreground">
        Upload a CSV and tell me what you want to learn. I&apos;ll create a
        reviewable plan before any calculations are run.
      </p>

      <div
        aria-busy={isReading}
        className={cn(
          "mt-8 rounded-2xl border border-dashed bg-muted/45 p-7 text-center transition-colors sm:p-9",
          isDragging && "border-emerald-700 bg-emerald-50",
          error && "border-destructive/60",
        )}
        onDragEnter={() => setIsDragging(true)}
        onDragLeave={() => setIsDragging(false)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          accept=".csv,text/csv"
          aria-label="Choose CSV file"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.item(0);
            if (file) {
              void selectFile(file);
            }
          }}
          ref={inputRef}
          type="file"
        />

        {isReading ? (
          <div aria-live="polite">
            <div className="mx-auto grid size-10 place-items-center rounded-xl border border-border bg-background text-muted-foreground">
              <LoaderCircle className="size-5 animate-spin" />
            </div>
            <p className="mt-3 text-base font-medium">Reading CSV preview</p>
            <p className="mt-1 text-sm text-muted-foreground">
              The original file stays unchanged.
            </p>
          </div>
        ) : selectedFile ? (
          <div aria-live="polite">
            <div className="mx-auto grid size-10 place-items-center rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="size-5" />
            </div>
            <p className="mt-3 text-base font-medium">CSV selected</p>
            <Card className="mx-auto mt-3 max-w-sm text-left shadow-none">
              <CardContent className="flex items-center gap-2 p-3">
                <FileSpreadsheet className="size-4 shrink-0 text-emerald-700" />
                <span className="min-w-0 flex-1 truncate text-base font-medium">
                  {selectedFile.name}
                </span>
                <span className="text-sm text-muted-foreground">
                  {formatFileSize(selectedFile.size)}
                </span>
              </CardContent>
            </Card>
            <Button
              className="mt-4"
              disabled={isReading}
              onClick={() => inputRef.current?.click()}
              size="sm"
              type="button"
              variant="outline"
            >
              Choose another file
            </Button>
          </div>
        ) : (
          <>
            <div className="mx-auto grid size-10 place-items-center rounded-xl border border-border bg-background text-muted-foreground">
              <Upload className="size-5" />
            </div>
            <p className="mt-3 text-base font-medium">Drop a CSV file here</p>
            <p className="mt-1 text-sm text-muted-foreground">
              or choose one from your computer · up to 10 MB
            </p>
            <Button
              className="mt-4"
              disabled={isReading}
              onClick={() => inputRef.current?.click()}
              size="sm"
              type="button"
            >
              Choose file
            </Button>
          </>
        )}
      </div>

      {error && (
        <p className="mt-3 text-center text-base text-destructive" role="alert">
          {error}
        </p>
      )}

      <p className="mt-4 text-center text-sm text-muted-foreground">
        The preview stays in the browser. A copy is sent to the planner.
      </p>
    </section>
  );
}
