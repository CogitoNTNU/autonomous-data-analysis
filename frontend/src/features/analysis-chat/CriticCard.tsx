import { Check } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import type { CritiqueView } from "@/types/planner";

export function CriticCard({
  critique,
  actions,
}: {
  critique: CritiqueView;
  actions?: ReactNode;
}) {
  return (
    <AgentDisclosure
      actions={actions}
      agent={agents.critic}
      detailsTitle="Review"
      statusBadge={critique.decision === "approved" ? (
        <Badge variant="outline" className="shrink-0 gap-1 border-emerald-600/20 bg-emerald-600/10 text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-400">
          <Check aria-hidden="true" className="size-3" />
          Approved
        </Badge>
      ) : undefined}
      summary={criticSummary(critique.decision)}
    >
      {critique.issues.length > 0 ? (
        <ul className="space-y-1.5 text-base leading-7 text-muted-foreground">
          {critique.issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      ) : (
        <p className="text-base leading-7 text-muted-foreground">
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
