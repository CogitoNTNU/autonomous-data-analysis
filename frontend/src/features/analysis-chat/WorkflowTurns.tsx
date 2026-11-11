import { Fragment } from "react";
import { Button } from "@/components/ui/button";
import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { AnalysisStages } from "@/features/analysis-chat/AnalysisStages";
import { ChatAnswerCard } from "@/features/analysis-chat/ChatAnswerCard";
import { DialogueTurns } from "@/features/analysis-chat/DialogueTurns";
import { ThinkingIndicator } from "@/features/analysis-chat/ThinkingIndicator";
import { UserMessage } from "@/features/analysis-chat/UserMessage";
import type { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";
import type { AnalysisRound } from "@/types/dialogue";

type Session = Pick<ReturnType<typeof usePlannerSession>,
  "busy" | "phase" | "plan" | "report" | "analysis" | "interpretation" | "critique" | "answer" | "error"
  | "rounds" | "dialogue" | "analysisRound" | "acceptsMessages" | "pendingMessage" | "submitQuestion"
  | "canRetryReview" | "retryReview"
>;

function stagesOf(round: AnalysisRound) {
  return { plan: round.plan, report: round.report, analysis: round.analysis, interpretation: round.interpretation, critique: round.critique };
}

export function WorkflowTurns({ session }: { session: Session }) {
  const turnsIn = (round: number) => session.dialogue.filter((turn) => turn.analysisRound === round);
  return (
    <>
      {session.rounds.map((round) => (
        <Fragment key={round.round}>
          <AnalysisStages {...stagesOf(round)} />
          <ChatAnswerCard answer={round.answer} figures={round.figures} tables={round.tables} />
          <DialogueTurns turns={turnsIn(round.round)} />
        </Fragment>
      ))}
      <AnalysisStages
        plan={session.plan}
        report={session.report}
        analysis={session.analysis}
        interpretation={session.interpretation}
        critique={session.critique}
        running={session.phase === "preprocessing"}
      />
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
          {session.canRetryReview && (
            <Button className="mt-3" variant="outline" onClick={session.retryReview}>Retry review</Button>
          )}
        </AgentTurn>
      )}
    </>
  );
}
