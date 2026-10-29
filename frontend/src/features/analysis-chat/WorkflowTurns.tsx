import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import { AnalysisReportCard } from "@/features/analysis-chat/AnalysisReportCard";
import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import { CriticCard } from "@/features/analysis-chat/CriticCard";
import { InterpretationCard } from "@/features/analysis-chat/InterpretationCard";
import { PreprocessingReportCard } from "@/features/analysis-chat/PreprocessingReportCard";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { WorkflowDetails } from "@/features/analysis-chat/WorkflowDetails";
import type { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";

type Session = Pick<ReturnType<typeof usePlannerSession>,
  "busy" | "phase" | "plan" | "report" | "analysis" | "interpretation" | "critique" | "answer" | "error"
>;

export function WorkflowTurns({ session }: { session: Session }) {
  const hasDetails = session.plan || session.report || session.analysis || session.interpretation || session.critique;
  return (
    <>
      {session.busy && <ThinkingIndicator agent={agents.assistant} label="Analyzing data…" />}
      {session.answer && (
        <ChatAnswerCard
          answer={session.answer}
          figures={session.analysis?.figures ?? []}
          tables={session.analysis?.tables ?? []}
        />
      )}
      {session.phase === "error" && session.error && (
        <AgentTurn agent={agents.assistant}>
          <p className="text-base leading-7 text-destructive" role="alert">{session.error}</p>
        </AgentTurn>
      )}
      {hasDetails && (
        <WorkflowDetails>
          {session.plan && <AnalysisPlanCard plan={session.plan} running={session.phase === "preprocessing"} />}
          {session.report && <PreprocessingReportCard report={session.report} />}
          {session.analysis && <AnalysisReportCard analysis={session.analysis} />}
          {session.interpretation && <InterpretationCard interpretation={session.interpretation} />}
          {session.critique && <CriticCard critique={session.critique} />}
        </WorkflowDetails>
      )}
    </>
  );
}
