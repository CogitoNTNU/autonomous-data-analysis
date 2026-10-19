import { FileSpreadsheet, RotateCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { formatFileSize } from "@/features/dataset-upload/validate-dataset-file";
import { AgentMark } from "@/features/workspace/AgentMark";
import type { DatasetPreview } from "@/types/dataset";

type DatasetPreviewPanelProps = {
  dataset: DatasetPreview;
  onReplaceDataset: () => void;
};

export function DatasetPreviewPanel({
  dataset,
  onReplaceDataset,
}: DatasetPreviewPanelProps) {
  return (
    <section aria-labelledby="dataset-preview-title" className="pt-9">
      <div className="flex gap-4">
        <AgentMark />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] leading-6" id="dataset-preview-title">
            I&apos;ve loaded <strong>{dataset.fileName}</strong>. It contains{" "}
            {dataset.rowCount.toLocaleString()} rows and {dataset.columnCount}{" "}
            columns. Here&apos;s a quick look at the data:
          </p>

          <Card className="mt-4 overflow-hidden shadow-none">
            <CardHeader className="flex-row items-center gap-3 space-y-0 border-b p-4">
              <div className="grid size-9 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
                <FileSpreadsheet className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <CardTitle className="truncate text-xs">
                  {dataset.fileName}
                </CardTitle>
                <CardDescription className="mt-1 text-[10px]">
                  {formatFileSize(dataset.fileSize)} · local preview
                </CardDescription>
              </div>
              <Badge className="text-[9px]" variant="secondary">
                CSV
              </Badge>
            </CardHeader>
            <CardContent className="p-0">
              {dataset.rows.length > 0 ? (
                <Table>
                  <TableHeader className="bg-muted/70">
                    <TableRow>
                      {dataset.columns.map((column) => (
                        <TableHead
                          className="whitespace-nowrap px-3 font-mono text-[9px]"
                          key={column}
                        >
                          {column}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataset.rows.map((row, rowIndex) => (
                      <TableRow key={`row-${rowIndex + 1}`}>
                        {dataset.columns.map((column, columnIndex) => (
                          <TableCell
                            className="max-w-48 truncate px-3 py-2.5 text-[10px]"
                            key={`${column}-${columnIndex}`}
                          >
                            {row[columnIndex] || (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="p-6 text-center text-xs text-muted-foreground">
                  This CSV has column headers but no data rows.
                </p>
              )}
            </CardContent>
          </Card>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-[10px] text-muted-foreground">
              Showing the first {dataset.rows.length} of{" "}
              {dataset.rowCount.toLocaleString()} rows.
            </p>
            <Button
              onClick={onReplaceDataset}
              size="sm"
              type="button"
              variant="outline"
            >
              <RotateCcw className="size-3.5" />
              Replace dataset
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
