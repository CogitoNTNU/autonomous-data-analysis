import { AnalysisChart } from "@/features/analysis-chat/AnalysisChart";
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
    <AgentDisclosure
      defaultOpen
      agent={agents.chat}
      detailsTitle="Final answer"
      summary="Prepared an answer"
    >
      <p className="text-base leading-7">{answer.text}</p>
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
  const figure = figures.find((item) => item.id === id);
  if (!figure?.image.trim()) {
    return (
      <p className="mt-3 text-base leading-7 text-muted-foreground">
        This chart could not be loaded
      </p>
    );
  }
  return (
    <div className="mt-5">
      <AnalysisChart figure={figure} label="Analysis chart" />
    </div>
  );
}
