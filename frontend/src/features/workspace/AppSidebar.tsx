import {
  ChevronRight,
  PanelLeftClose,
  FileSpreadsheet,
  Plus,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { AgentMark } from "@/features/workspace/AgentMark";
import type { DatasetPreview } from "@/types/dataset";

type AppSidebarProps = {
  dataset: DatasetPreview | null;
  onClose?: () => void;
  onNewAnalysis: () => void;
  onReplaceDataset: () => void;
};

export function AppSidebar({
  dataset,
  onClose,
  onNewAnalysis,
  onReplaceDataset,
}: AppSidebarProps) {
  const [isDatasetOpen, setIsDatasetOpen] = useState(true);

  return (
    <aside className="hidden w-[260px] shrink-0 flex-col border-r border-border/40 bg-sidebar p-3 lg:flex">
      <div className="flex h-11 items-center gap-2.5 px-2">
        <AgentMark compact />
        <span className="min-w-0 flex-1 text-[13px] font-semibold">Data Analysis Planner</span>
        {onClose && (
          <Button aria-label="Close sidebar" title="Close sidebar" variant="ghost" size="icon" onClick={onClose} aria-controls="workspace-sidebar" aria-expanded={true}>
            <PanelLeftClose className="size-4" />
          </Button>
        )}
      </div>

      <Button
        className="mt-3 w-full justify-start"
        onClick={onNewAnalysis}
        size="sm"
        type="button"
        variant="ghost"
      >
        <Plus className="size-4" />
        New analysis
      </Button>

      <nav aria-label="Recent analyses" className="mt-5">
        <p className="px-3 text-[10px] font-medium text-muted-foreground">
          Recent
        </p>
        <p className="mt-2 px-3 text-[10px] leading-4 text-muted-foreground">
          No saved analyses yet.
        </p>
      </nav>

      {dataset && (
        <div className="mt-6 min-h-0">
          <p className="px-3 text-[10px] font-medium text-muted-foreground">
            Dataset
          </p>
          <Card className="mt-2 shadow-none">
            <button
              aria-expanded={isDatasetOpen}
              className="flex w-full items-center gap-2.5 p-3 text-left"
              onClick={() => setIsDatasetOpen((open) => !open)}
              type="button"
            >
              <span className="grid size-8 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
                <FileSpreadsheet className="size-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[11px] font-medium">
                  {dataset.fileName}
                </span>
                <span className="mt-0.5 block text-[9px] text-muted-foreground">
                  {dataset.rowCount.toLocaleString()} rows ·{" "}
                  {dataset.columnCount} columns
                </span>
              </span>
              <ChevronRight
                className={`size-3.5 text-muted-foreground transition-transform ${
                  isDatasetOpen ? "rotate-90" : ""
                }`}
              />
            </button>
            {isDatasetOpen && (
              <CardContent className="px-3 pb-3 pt-0">
                <Separator />
                <ul className="mt-2 space-y-1.5" aria-label="Dataset columns">
                  {dataset.columns.slice(0, 5).map((column) => (
                    <li
                      className="truncate font-mono text-[9px] text-muted-foreground"
                      key={column}
                    >
                      {column}
                    </li>
                  ))}
                </ul>
                {dataset.columns.length > 5 && (
                  <p className="mt-2 text-[9px] text-muted-foreground">
                    +{dataset.columns.length - 5} more columns
                  </p>
                )}
                <Button
                  className="mt-2 h-auto p-0 text-[9px] text-emerald-700 hover:bg-transparent hover:underline"
                  onClick={onReplaceDataset}
                  type="button"
                  variant="ghost"
                >
                  Replace file
                </Button>
              </CardContent>
            )}
          </Card>
        </div>
      )}

      <div className="mt-auto flex items-center gap-2.5 rounded-lg p-2">
        <div
          aria-hidden="true"
          className="grid size-8 place-items-center rounded-full bg-[#d8c7b8] text-[10px] font-semibold text-[#352b25]"
        >
          WS
        </div>
        <div>
          <p className="text-[11px] font-medium">Your workspace</p>
          <p className="text-[9px] text-muted-foreground">Local prototype</p>
        </div>
      </div>
    </aside>
  );
}
