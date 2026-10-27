import type { InterpretationAsk, PlannerClient } from "@/api/planner";
import { agents, type AgentIdentity } from "@/features/analysis-chat/agents";
import type { AnalysisReport, ChatAnswer, CritiqueView, InterpretationView, PreprocessingReport } from "@/types/planner";

export type WorkflowStage = "preprocessing" | "analysis" | "interpretation" | "critic" | "chat";
export type ContinueUpdate =
  | { phase: WorkflowStage }
  | { phase: "analysis_ready"; report: PreprocessingReport }
  | { phase: "interpretation_ready"; analysis: AnalysisReport }
  | { phase: "critic_ready"; interpretation: InterpretationView }
  | { phase: "chat_ready"; critique: CritiqueView }
  | { phase: "complete"; answer: ChatAnswer }
  | { phase: "error"; message: string; agent: AgentIdentity };

export async function continueReviewedPlan(
  client: PlannerClient,
  input: InterpretationAsk,
  publish: (update: ContinueUpdate) => void,
  stage: WorkflowStage = "preprocessing",
  interpretation: InterpretationView | null = null,
  critique: CritiqueView | null = null,
): Promise<void> {
  try {
    publish({ phase: stage });
    switch (stage) {
      case "preprocessing": {
        const result = await client.preprocess(input);
        if (result.status === "error") throw new Error(result.message);
        publish({ phase: "analysis_ready", report: result.report });
        return;
      }
      case "analysis": {
        const result = await client.analyze(input);
        if (result.status === "error") throw new Error(result.message);
        publish({ phase: "interpretation_ready", analysis: result.analysis });
        return;
      }
      case "interpretation": {
        const result = await client.interpret(input);
        if (result.status === "error") throw new Error(result.message);
        publish({ phase: "critic_ready", interpretation: result.interpretation });
        return;
      }
      case "critic": {
        if (!interpretation) throw new Error("Interpretation is required before review");
        const result = await client.critique({ ...input, interpretation });
        if (result.status === "error") throw new Error(result.message);
        publish({ phase: "chat_ready", critique: result.critique });
        return;
      }
      case "chat": {
        if (!interpretation || !critique) throw new Error("Interpretation and review are required before presenting the answer");
        const result = await client.present({ interpretation, critique });
        if (result.status === "error") throw new Error(result.message);
        publish({ phase: "complete", answer: result.answer });
      }
    }
  } catch (reason: unknown) {
    publish({ phase: "error", message: reason instanceof Error ? reason.message : "The workflow request failed", agent: agents[stage] });
  }
}
