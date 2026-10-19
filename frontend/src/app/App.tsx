import { useState } from "react";

import { DatasetPreviewPanel } from "@/features/dataset-preview/DatasetPreviewPanel";
import { DatasetUpload } from "@/features/dataset-upload/DatasetUpload";
import { AppSidebar } from "@/features/workspace/AppSidebar";
import { WorkspaceHeader } from "@/features/workspace/WorkspaceHeader";
import type { DatasetPreview } from "@/types/dataset";

export function App() {
  const [dataset, setDataset] = useState<DatasetPreview | null>(null);

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <AppSidebar
        dataset={dataset}
        onNewAnalysis={() => setDataset(null)}
        onReplaceDataset={() => setDataset(null)}
      />
      <main className="flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader datasetName={dataset?.fileName} />
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[760px] px-5 pb-16 sm:px-6">
            {dataset ? (
              <DatasetPreviewPanel
                dataset={dataset}
                onReplaceDataset={() => setDataset(null)}
              />
            ) : (
              <DatasetUpload onDatasetReady={setDataset} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
