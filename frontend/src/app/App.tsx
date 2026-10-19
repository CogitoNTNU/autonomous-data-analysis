import { useEffect, useState } from "react";

import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import { AnalysisQuestionComposer } from "@/features/analysis-chat/AnalysisQuestionComposer";
import { ClarificationPrompt } from "@/features/analysis-chat/ClarificationPrompt";
import { QuestionSuggestions } from "@/features/analysis-chat/QuestionSuggestions";
import { SubmittedQuestion } from "@/features/analysis-chat/SubmittedQuestion";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { getPrototypeClarification } from "@/features/analysis-chat/prototype-clarification";
import { createPrototypeAnalysisPlan } from "@/features/analysis-chat/prototype-plan";
import { DatasetPreviewPanel } from "@/features/dataset-preview/DatasetPreviewPanel";
import { DatasetUpload } from "@/features/dataset-upload/DatasetUpload";
import { AppSidebar } from "@/features/workspace/AppSidebar";
import { WorkspaceHeader } from "@/features/workspace/WorkspaceHeader";
import { useTheme } from "@/features/workspace/use-theme";
import type { DatasetPreview } from "@/types/dataset";
import type {
  ClarificationOption,
  ClarificationRequest,
} from "@/types/planner";

type PlannerPhase =
  | "idle"
  | "thinking"
  | "clarification"
  | "clarification_input"
  | "plan";

const PLANNER_DELAY_MS = 500;

export function App() {
  const { theme, toggleTheme } = useTheme();
  const [dataset, setDataset] = useState<DatasetPreview | null>(null);
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(
    null,
  );
  const [phase, setPhase] = useState<PlannerPhase>("idle");
  const [clarification, setClarification] =
    useState<ClarificationRequest | null>(null);
  const [clarificationAnswer, setClarificationAnswer] = useState<string | null>(
    null,
  );

  useEffect(() => {
    if (
      phase !== "thinking" ||
      !dataset ||
      !submittedQuestion
    ) {
      return;
    }

    const timeout = window.setTimeout(() => {
      const request = clarificationAnswer
        ? null
        : getPrototypeClarification(submittedQuestion, dataset.columns);

      if (request) {
        setClarification(request);
        setPhase("clarification");
        return;
      }

      setPhase("plan");
    }, PLANNER_DELAY_MS);

    return () => window.clearTimeout(timeout);
  }, [clarificationAnswer, dataset, phase, submittedQuestion]);

  function resetQuestion() {
    setQuestion("");
    setSubmittedQuestion(null);
    setPhase("idle");
    setClarification(null);
    setClarificationAnswer(null);
  }

  function replaceDataset() {
    setDataset(null);
    resetQuestion();
  }

  function submitQuestion(nextQuestion: string) {
    if (phase === "clarification_input") {
      setClarificationAnswer(nextQuestion);
      setQuestion("");
      setPhase("thinking");
      return;
    }

    setSubmittedQuestion(nextQuestion);
    setQuestion("");
    setClarification(null);
    setClarificationAnswer(null);
    setPhase("thinking");
  }

  function answerClarification(option: ClarificationOption) {
    if (option.id === "custom") {
      setQuestion("By largest, I mean ");
      setPhase("clarification_input");
      return;
    }

    setClarificationAnswer(option.label);
    setPhase("thinking");
  }

  const analysisPlan = submittedQuestion
    ? createPrototypeAnalysisPlan(submittedQuestion)
    : null;

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <AppSidebar
        dataset={dataset}
        onNewAnalysis={resetQuestion}
        onReplaceDataset={replaceDataset}
      />
      <main className="relative flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader
          datasetName={dataset?.fileName}
          hasDataset={dataset !== null}
          onNewAnalysis={resetQuestion}
          onToggleTheme={toggleTheme}
          theme={theme}
        />
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
                    {clarificationAnswer && (
                      <SubmittedQuestion question={clarificationAnswer} />
                    )}
                    {phase === "thinking" && <ThinkingIndicator />}
                    {phase === "plan" && analysisPlan && (
                      <AnalysisPlanCard plan={analysisPlan} />
                    )}
                    {(phase === "clarification" ||
                      phase === "clarification_input") &&
                      clarification && (
                        <ClarificationPrompt
                          awaitingCustomAnswer={phase === "clarification_input"}
                          clarification={clarification}
                          onSelect={answerClarification}
                        />
                      )}
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
          disabled={
            phase !== "idle" && phase !== "clarification_input"
          }
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
