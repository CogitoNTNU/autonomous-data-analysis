import type { WorkflowSnapshot } from "@/api/workflows";
import type { AnalysisRound } from "@/types/dialogue";

// The backend clears a round's answer when the next round starts, so keep the last answer seen.
export function archiveRound(
  rounds: AnalysisRound[],
  previous: WorkflowSnapshot | null,
  next: WorkflowSnapshot,
): AnalysisRound[] {
  if (!previous || previous.runId !== next.runId) return [];
  if (!previous.answer || previous.analysisRound >= next.analysisRound) return rounds;
  return [...rounds, {
    round: previous.analysisRound,
    answer: previous.answer,
    figures: previous.analysis?.figures ?? [],
    tables: previous.analysis?.tables ?? [],
  }];
}
