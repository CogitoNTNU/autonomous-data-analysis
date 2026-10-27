import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import type { AnalysisFigure, ChatAnswer } from "@/types/planner";

export function ChatAnswerCard({
  answer,
  figures,
}: {
  answer: ChatAnswer;
  figures: AnalysisFigure[];
}) {
  return (
    <AgentDisclosure agent={agents.chat} defaultOpen summary="Prepared an answer">
      <p className="text-xs leading-5">{answer.text}</p>
      <TextList
        items={answer.findings.map((finding) => finding.claim)}
        title="Findings"
      />
      <AnswerCharts figureIds={answer.figureIds} figures={figures} />
      <TextList items={answer.limitations} title="Limitations" />
      <TextList items={answer.followUps} title="Follow-up questions" />
    </AgentDisclosure>
  );
}

function AnswerCharts({
  figureIds,
  figures,
}: {
  figureIds: string[];
  figures: AnalysisFigure[];
}) {
  return figureIds.map((id, index) => (
    <AnswerChart figures={figures} id={id} key={`${id}-${index}`} />
  ));
}

function AnswerChart({ id, figures }: { id: string; figures: AnalysisFigure[] }) {
  const image = figures.find((figure) => figure.id === id)?.image;
  if (!image?.trim()) {
    return (
      <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
        This chart could not be loaded
      </p>
    );
  }
  return (
    <img
      alt="Analysis chart"
      className="mt-3 max-w-full rounded-lg border border-border"
      src={image}
    />
  );
}
