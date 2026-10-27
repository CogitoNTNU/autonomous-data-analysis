import { ChatScrollArea } from "@/features/analysis-chat/ChatScrollArea";
import { useState } from "react";
import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisQuestionComposer } from "@/features/analysis-chat/AnalysisQuestionComposer";
import { ClarificationPrompt } from "@/features/analysis-chat/ClarificationPrompt";
import { QuestionSuggestions } from "@/features/analysis-chat/QuestionSuggestions";
import { WorkflowTurns } from "@/features/analysis-chat/WorkflowTurns";
import { SubmittedQuestion } from "@/features/analysis-chat/SubmittedQuestion";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";
import type { WorkflowClient } from "@/api/workflows";
import { DatasetPreviewPanel } from "@/features/dataset-preview/DatasetPreviewPanel";
import { DatasetUpload } from "@/features/dataset-upload/DatasetUpload";
import { AppSidebar } from "@/features/workspace/AppSidebar";
import { WorkspaceHeader } from "@/features/workspace/WorkspaceHeader";
import { useTheme } from "@/features/workspace/use-theme";

type AppProps = {
  planner?: WorkflowClient;
};

export function App({ planner }: AppProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useTheme();
  const session = usePlannerSession(planner);
  const waiting = session.busy || session.phase === "complete" || session.phase === "clarification";

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <div
        className={`hidden shrink-0 overflow-hidden transition-[width,opacity] duration-300 ease-in-out lg:flex ${sidebarOpen ? "w-[260px] opacity-100" : "w-0 opacity-0"}`}
        id="workspace-sidebar"
        inert={!sidebarOpen}
        aria-hidden={!sidebarOpen}
      >
      <AppSidebar
        dataset={session.dataset}
        onNewAnalysis={session.resetQuestion}
        onReplaceDataset={session.replaceDataset}
        onClose={() => setSidebarOpen(false)}
      />
      </div>
      <main className="relative flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
          hasDataset={session.dataset !== null}
          onNewAnalysis={session.resetQuestion}
          onToggleTheme={toggleTheme}
          theme={theme}
        />
        <ChatScrollArea>
          <div className="mx-auto w-full max-w-[800px] pb-10">
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
        </ChatScrollArea>
        <AnalysisQuestionComposer
          disabled={waiting || session.dataset === null}
          finished={session.phase === "complete"}
          hasDataset={session.dataset !== null}
          onChange={session.setQuestion}
          onSubmit={session.submitQuestion}
          question={session.question}
          suggestions={
            session.dataset && !session.submittedQuestion ? (
              <QuestionSuggestions
                dataset={session.dataset}
                onSelect={session.submitQuestion}
              />
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
  const editingDisabled = ["thinking", "preprocessing", "analysis", "interpretation", "critic", "chat"].includes(session.phase);
  function editQuestion(question: string) {
    session.editQuestion(question);
    requestAnimationFrame(() => {
      document.querySelector<HTMLTextAreaElement>('textarea[aria-label="Analysis question"]')?.focus();
    });
  }
  return (
    <>
      <DatasetPreviewPanel dataset={dataset} onReplaceDataset={session.acceptDataset} />
      {session.submittedQuestion ? (
        <>
          <SubmittedQuestion question={session.submittedQuestion} onEdit={editQuestion} editDisabled={editingDisabled} />
          {session.clarificationAnswer && (
            <SubmittedQuestion question={session.clarificationAnswer} onEdit={editQuestion} editDisabled={editingDisabled} />
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
      <p className="text-base leading-7 text-destructive" role="alert">
        {message}
      </p>
    </AgentTurn>
  );
}
