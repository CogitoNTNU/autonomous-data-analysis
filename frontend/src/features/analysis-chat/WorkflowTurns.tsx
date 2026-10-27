import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import { AnalysisReportCard } from "@/features/analysis-chat/AnalysisReportCard";
import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import { CriticCard } from "@/features/analysis-chat/CriticCard";
import { InterpretationCard } from "@/features/analysis-chat/InterpretationCard";
import { PreprocessingReportCard } from "@/features/analysis-chat/PreprocessingReportCard";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import type { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";

const running = {
  preprocessing: {
    agent: agents.preprocessing,
  },
  analysis: {
    agent: agents.analysis,
  },
  interpretation: {
    agent: agents.interpretation,
  },
  critic: {
    agent: agents.critic,
  },
  chat: {
    agent: agents.chat,
  },
} as const;

type Session = ReturnType<typeof usePlannerSession>;

export function WorkflowTurns({ session }: { session: Session }) {
  const active = running[session.phase as keyof typeof running];
  return (
    <>
      {session.plan && (
        <AnalysisPlanCard
          plan={session.plan}
          running={session.phase === "preprocessing"}
        />
      )}
      {session.report && <PreprocessingReportCard report={session.report} />}
      {session.analysis && <AnalysisReportCard analysis={session.analysis} />}
      {session.interpretation && (
        <InterpretationCard interpretation={session.interpretation} />
      )}
      {session.critique && <CriticCard critique={session.critique} />}
      {session.answer && (
        <ChatAnswerCard
          answer={session.answer}
          figures={session.analysis?.figures ?? []}
        />
      )}
      {active && <ThinkingIndicator agent={active.agent} />}
      {session.phase === "error" && session.error && (
        <AgentTurn agent={session.errorAgent}>
          <p className="text-base leading-7 text-destructive" role="alert">
            {session.error}
          </p>
        </AgentTurn>
      )}
    </>
  );
}
