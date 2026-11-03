import { Fragment } from "react";
import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import { AnalysisReportCard } from "@/features/analysis-chat/AnalysisReportCard";
import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import { CriticCard } from "@/features/analysis-chat/CriticCard";
import { DialogueTurns } from "@/features/analysis-chat/DialogueTurns";
import { InterpretationCard } from "@/features/analysis-chat/InterpretationCard";
import { PreprocessingReportCard } from "@/features/analysis-chat/PreprocessingReportCard";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { UserMessage } from "@/features/analysis-chat/UserMessage";
import { WorkflowDetails } from "@/features/analysis-chat/WorkflowDetails";
import type { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";

type Session = Pick<ReturnType<typeof usePlannerSession>,
  "busy" | "phase" | "plan" | "report" | "analysis" | "interpretation" | "critique" | "answer" | "error"
  | "rounds" | "dialogue" | "analysisRound" | "acceptsMessages" | "pendingMessage" | "submitQuestion"
>;

export function WorkflowTurns({ session }: { session: Session }) {
  const hasDetails = session.plan || session.report || session.analysis || session.interpretation || session.critique;
  const turnsIn = (round: number) => session.dialogue.filter((turn) => turn.analysisRound === round);
  return (
    <>
      {session.rounds.map((round) => (
        <Fragment key={round.round}>
          <ChatAnswerCard answer={round.answer} figures={round.figures} tables={round.tables} />
          <DialogueTurns turns={turnsIn(round.round)} />
        </Fragment>
      ))}
      {session.answer && (
        <ChatAnswerCard
          answer={session.answer}
          figures={session.analysis?.figures ?? []}
          tables={session.analysis?.tables ?? []}
          onFollowUp={session.acceptsMessages && !session.busy ? session.submitQuestion : undefined}
        />
      )}
      <DialogueTurns turns={turnsIn(session.analysisRound)} />
      {session.pendingMessage && <UserMessage text={session.pendingMessage} />}
      {session.busy && (
        <ThinkingIndicator agent={agents.assistant} label={session.answer ? "Writing a reply…" : "Analyzing data…"} />
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
