import type { ReactNode } from "react";
import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import { MarkdownText } from "@/features/analysis-chat/MarkdownText";
import type { InterpretationView } from "@/types/planner";

export function InterpretationCard({
  interpretation,
  actions,
}: {
  interpretation: InterpretationView;
  actions?: ReactNode;
}) {
  return (
    <AgentDisclosure
      actions={actions}
      agent={agents.interpretation}
      detailsTitle="Interpretation"
      summary="Interpretation finished"
    >
      <MarkdownText text={interpretation.summary} />
      <TextList
        items={interpretation.findings.map((finding) => finding.claim)}
        title="Findings"
      />
      <TextList items={interpretation.limitations} title="Limitations" />
    </AgentDisclosure>
  );
}
