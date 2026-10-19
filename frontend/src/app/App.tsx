import { useState } from "react";

import { AnalysisQuestionComposer } from "@/features/analysis-chat/AnalysisQuestionComposer";
import { QuestionSuggestions } from "@/features/analysis-chat/QuestionSuggestions";
import { SubmittedQuestion } from "@/features/analysis-chat/SubmittedQuestion";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { DatasetPreviewPanel } from "@/features/dataset-preview/DatasetPreviewPanel";
import { DatasetUpload } from "@/features/dataset-upload/DatasetUpload";
import { AppSidebar } from "@/features/workspace/AppSidebar";
import { WorkspaceHeader } from "@/features/workspace/WorkspaceHeader";
import type { DatasetPreview } from "@/types/dataset";

export function App() {
  const [dataset, setDataset] = useState<DatasetPreview | null>(null);
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(
    null,
  );
  const [isThinking, setIsThinking] = useState(false);

  function resetQuestion() {
    setQuestion("");
    setSubmittedQuestion(null);
    setIsThinking(false);
  }

  function replaceDataset() {
    setDataset(null);
    resetQuestion();
  }

  function submitQuestion(nextQuestion: string) {
    setSubmittedQuestion(nextQuestion);
    setQuestion("");
    setIsThinking(true);
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <AppSidebar
        dataset={dataset}
        onNewAnalysis={resetQuestion}
        onReplaceDataset={replaceDataset}
      />
      <main className="relative flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader datasetName={dataset?.fileName} />
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[760px] px-5 pb-44 sm:px-6">
            {dataset ? (
              <>
                <DatasetPreviewPanel
                  dataset={dataset}
                  onReplaceDataset={replaceDataset}
                />
                {submittedQuestion ? (
                  <>
                    <SubmittedQuestion question={submittedQuestion} />
                    {isThinking && <ThinkingIndicator />}
                  </>
                ) : (
                  <QuestionSuggestions
                    dataset={dataset}
                    onSelect={submitQuestion}
                  />
                )}
              </>
            ) : (
              <DatasetUpload
                onDatasetReady={(nextDataset) => {
                  setDataset(nextDataset);
                  resetQuestion();
                }}
              />
            )}
          </div>
        </div>
        <AnalysisQuestionComposer
          disabled={submittedQuestion !== null || isThinking}
          hasDataset={dataset !== null}
          onChange={setQuestion}
          onReplaceDataset={replaceDataset}
          onSubmit={submitQuestion}
          question={question}
        />
      </main>
    </div>
  );
}
