import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import type { InterpretationView } from "@/types/planner";

export function InterpretationCard({
  interpretation,
}: {
  interpretation: InterpretationView;
}) {
  return (
    <AgentDisclosure agent={agents.interpretation} summary="Interpretation finished">
      <p className="text-xs leading-5">{interpretation.summary}</p>
      <TextList items={interpretation.findings} title="Findings" />
      <TextList items={interpretation.limitations} title="Limitations" />
    </AgentDisclosure>
  );
}
