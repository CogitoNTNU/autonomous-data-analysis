import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import type { CritiqueView } from "@/types/planner";

export function CriticCard({ critique }: { critique: CritiqueView }) {
  return (
    <AgentDisclosure agent={agents.critic} summary={criticSummary(critique.decision)}>
      {critique.issues.length > 0 ? (
        <ul className="space-y-1.5 text-[11px] leading-4 text-muted-foreground">
          {critique.issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] leading-4 text-muted-foreground">
          No issues were raised.
        </p>
      )}
      <TextList items={critique.requiredChanges} title="Required changes" />
    </AgentDisclosure>
  );
}

function criticSummary(decision: CritiqueView["decision"]): string {
  if (decision === "approved") {
    return "Critic approved";
  }
  if (decision === "revise") {
    return "Critic asked for a revision";
  }
  return "Critic could not complete the review";
}
