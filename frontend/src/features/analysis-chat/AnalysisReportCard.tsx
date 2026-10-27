import type { ReactNode } from "react";
import { AnalysisChart } from "@/features/analysis-chat/AnalysisChart";
import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { WarningList } from "@/features/analysis-chat/WarningList";
import type { AnalysisReport } from "@/types/planner";

export function AnalysisReportCard({
  analysis,
  actions,
}: {
  analysis: AnalysisReport;
  actions?: ReactNode;
}) {
  const count = analysis.steps.length;
  const label = count === 1 ? "result" : "results";
  return (
    <AgentDisclosure
      actions={actions}
      agent={agents.analysis}
      detailsTitle="Analysis results"
      summary={`Analysis finished, ${count} ${label}`}
    >
      {analysis.steps.length > 0 ? (
        <ul className="space-y-3">
          {analysis.steps.map((step) => (
            <li key={step.id}>
              <p className="text-base font-semibold">{title(step.method)}</p>
              <p className="mt-1 text-base leading-7 text-muted-foreground">
                {step.detail}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-base leading-7 text-muted-foreground">
          No analysis steps were run.
        </p>
      )}
      {analysis.figures.length > 0 && (
        <div className="mt-5 space-y-5">
          {analysis.figures.map((figure, index) => (
            <AnalysisChart
              figure={figure}
              key={figure.id}
              label={analysis.figures.length === 1 ? "Analysis chart" : `Analysis chart ${index + 1}`}
            />
          ))}
        </div>
      )}
      <WarningList warnings={analysis.warnings} />
    </AgentDisclosure>
  );
}

function title(method: string): string {
  return method.replaceAll("_", " ");
}
