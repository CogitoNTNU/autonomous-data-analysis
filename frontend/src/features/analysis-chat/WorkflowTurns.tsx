import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import { PreprocessingReportCard } from "@/features/analysis-chat/PreprocessingReportCard";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import {
  AnalysisReportCard,
  ChatAnswerCard,
  CriticCard,
  InterpretationCard,
} from "@/features/analysis-chat/WorkflowCards";
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
  function nextAction(phase: Session["phase"], label: string) {
    return session.phase === phase ? (
      <div className="mt-3 flex justify-end border-t border-border/50 pt-2">
        <Button variant="ghost" size="sm" className="group gap-2 text-sm text-muted-foreground hover:text-foreground" onClick={() => void session.runNextAgent()}>{label}<ArrowRight aria-hidden="true" className="size-3.5 text-emerald-700/70 transition-colors group-hover:text-emerald-700 group-focus-visible:text-emerald-700 dark:text-emerald-400/70 dark:group-hover:text-emerald-400 dark:group-focus-visible:text-emerald-400" /></Button>
      </div>
    ) : undefined;
  }
  const active = running[session.phase as keyof typeof running];
  return (
    <>
      {session.plan && (
        <AnalysisPlanCard
          onRun={
            session.phase === "plan"
              ? () => {
                  void session.runNextAgent();
                }
              : undefined
          }
          plan={session.plan}
          running={session.phase === "preprocessing"}
        />
      )}
      {session.report && <PreprocessingReportCard report={session.report} actions={nextAction("analysis_ready", "Run analysis")} />}
      {session.analysis && <AnalysisReportCard analysis={session.analysis} actions={nextAction("interpretation_ready", "Interpret results")} />}
      {session.interpretation && (
        <InterpretationCard interpretation={session.interpretation} actions={nextAction("critic_ready", "Review findings")} />
      )}
      {session.critique && <CriticCard critique={session.critique} actions={nextAction("chat_ready", "Show final answer")} />}
      {session.answer && <ChatAnswerCard answer={session.answer} />}
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
