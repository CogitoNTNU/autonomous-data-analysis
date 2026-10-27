import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisQuestionComposer } from "@/features/analysis-chat/AnalysisQuestionComposer";
import { ClarificationPrompt } from "@/features/analysis-chat/ClarificationPrompt";
import { QuestionSuggestions } from "@/features/analysis-chat/QuestionSuggestions";
import { WorkflowTurns } from "@/features/analysis-chat/WorkflowTurns";
import { SubmittedQuestion } from "@/features/analysis-chat/SubmittedQuestion";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";
import type { PlannerClient } from "@/api/planner";
import { DatasetPreviewPanel } from "@/features/dataset-preview/DatasetPreviewPanel";
import { DatasetUpload } from "@/features/dataset-upload/DatasetUpload";
import { AppSidebar } from "@/features/workspace/AppSidebar";
import { WorkspaceHeader } from "@/features/workspace/WorkspaceHeader";
import { useTheme } from "@/features/workspace/use-theme";

type AppProps = {
  planner?: PlannerClient;
};

export function App({ planner }: AppProps) {
  const { theme, toggleTheme } = useTheme();
  const session = usePlannerSession(planner);
  const waiting =
    session.phase === "thinking" ||
    session.phase === "plan" ||
    session.phase === "preprocessing" ||
    session.phase === "analysis" ||
    session.phase === "interpretation" ||
    session.phase === "critic" ||
    session.phase === "chat" ||
    session.phase === "complete" ||
    session.phase === "clarification";

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <AppSidebar
        dataset={session.dataset}
        onNewAnalysis={session.resetQuestion}
        onReplaceDataset={session.replaceDataset}
      />
      <main className="relative flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader
          datasetName={session.dataset?.fileName}
          hasDataset={session.dataset !== null}
          onNewAnalysis={session.resetQuestion}
          onToggleTheme={toggleTheme}
          theme={theme}
        />
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[760px] px-5 pb-8 sm:px-6">
            {session.dataset ? (
              <DatasetConversation dataset={session.dataset} session={session} />
            ) : (
              <>
                <DatasetUpload
                  onDatasetReady={(preview, file) => {
                    void session.acceptDataset(preview, file);
                  }}
                />
                {session.error && (
                  <PlannerError agent={agents.planner} message={session.error} />
                )}
              </>
            )}
          </div>
        </div>
        <AnalysisQuestionComposer
          disabled={waiting || session.dataset === null}
          finished={session.phase === "complete"}
          hasDataset={session.dataset !== null}
          onChange={session.setQuestion}
          onReplaceDataset={session.replaceDataset}
          onSubmit={session.submitQuestion}
          question={session.question}
          suggestions={
            session.dataset && !session.submittedQuestion ? (
              <QuestionSuggestions dataset={session.dataset} onSelect={session.submitQuestion} />
            ) : null
          }
        />
      </main>
    </div>
  );
}

function DatasetConversation({
  dataset,
  session,
}: {
  dataset: NonNullable<ReturnType<typeof usePlannerSession>["dataset"]>;
  session: ReturnType<typeof usePlannerSession>;
}) {
  return (
    <>
      <DatasetPreviewPanel
        dataset={dataset}
        onReplaceDataset={session.replaceDataset}
      />
      {session.submittedQuestion ? (
        <>
          <SubmittedQuestion question={session.submittedQuestion} />
          {session.clarificationAnswer && (
            <SubmittedQuestion question={session.clarificationAnswer} />
          )}
          {session.phase === "thinking" && <ThinkingIndicator />}
          {session.plan && <WorkflowTurns session={session} />}
          {(session.phase === "clarification" ||
            session.phase === "clarification_input") &&
            session.clarification && (
              <ClarificationPrompt
                awaitingCustomAnswer={session.phase === "clarification_input"}
                clarification={session.clarification}
                onSelect={session.answerClarification}
              />
            )}
          {session.phase === "error" && session.error && !session.plan && (
            <PlannerError agent={agents.planner} message={session.error} />
          )}
        </>
      ) : null}
    </>
  );
}

function PlannerError({
  agent,
  message,
}: {
  agent: (typeof agents)[keyof typeof agents];
  message: string;
}) {
  return (
    <AgentTurn agent={agent}>
      <p className="text-xs text-destructive" role="alert">
        {message}
      </p>
    </AgentTurn>
  );
}
