import type { AnalysisAsk, InterpretationAsk, PlannerClient } from "@/api/planner";
import { agents, type AgentIdentity } from "@/features/analysis-chat/agents";
import type {
  AnalysisReport,
  ChatAnswer,
  CritiqueView,
  InterpretationView,
  PreprocessingReport,
} from "@/types/planner";

export type ContinueUpdate =
  | { phase: "preprocessing" }
  | { phase: "analysis"; report: PreprocessingReport }
  | { phase: "interpretation"; analysis: AnalysisReport }
  | { phase: "critic"; interpretation: InterpretationView }
  | { phase: "chat"; critique: CritiqueView }
  | { phase: "complete"; answer: ChatAnswer }
  | { phase: "error"; message: string; agent: AgentIdentity };

export async function continueReviewedPlan(
  client: PlannerClient,
  input: InterpretationAsk,
  publish: (update: ContinueUpdate) => void,
): Promise<void> {
  let agent: AgentIdentity = agents.preprocessing;
  try {
    publish({ phase: "preprocessing" });
    const prepared = await client.preprocess(input);
    if (prepared.status === "error") {
      publish({ phase: "error", message: prepared.message, agent });
      return;
    }
    agent = agents.analysis;
    publish({ phase: "analysis", report: prepared.report });
    const analyzed = await client.analyze(analysisAsk(input));
    if (analyzed.status === "error") {
      publish({ phase: "error", message: analyzed.message, agent });
      return;
    }
    agent = agents.interpretation;
    publish({ phase: "interpretation", analysis: analyzed.analysis });
    const interpreted = await client.interpret({
      ...input,
      results: analyzed.analysis.results,
      artifacts: analyzed.analysis.artifacts,
    });
    if (interpreted.status === "error") {
      publish({ phase: "error", message: interpreted.message, agent });
      return;
    }
    agent = agents.critic;
    publish({ phase: "critic", interpretation: interpreted.interpretation });
    const reviewed = await client.critique({
      ...input,
      results: analyzed.analysis.results,
      artifacts: analyzed.analysis.artifacts,
      interpretation: interpreted.interpretation,
    });
    if (reviewed.status === "error") {
      publish({ phase: "error", message: reviewed.message, agent });
      return;
    }
    agent = agents.chat;
    publish({ phase: "chat", critique: reviewed.critique });
    const presented = await client.present({
      interpretation: interpreted.interpretation,
      critique: reviewed.critique,
    });
    if (presented.status === "error") {
      publish({ phase: "error", message: presented.message, agent });
      return;
    }
    publish({ phase: "complete", answer: presented.answer });
  } catch (reason: unknown) {
    publish({ phase: "error", message: messageFrom(reason), agent });
  }
}

function analysisAsk(input: InterpretationAsk): AnalysisAsk {
  return { datasetId: input.datasetId, csv: input.csv, plan: input.plan };
}

function messageFrom(reason: unknown): string {
  if (reason instanceof Error && reason.message.trim()) {
    return reason.message;
  }
  return "The planner could not be reached";
}
