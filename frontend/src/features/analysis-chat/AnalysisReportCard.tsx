import type { ReactNode } from "react";
import { AnalysisSummaryTable } from "@/features/analysis-chat/AnalysisSummaryTable";
import { AnalysisChartGallery } from "@/features/analysis-chat/AnalysisChartGallery";
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
              <h3 className="text-lg font-semibold leading-7 tracking-tight">{title(step.method)}</h3>
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
      {analysis.tables?.map((table) => <AnalysisSummaryTable key={table.id} table={table} />)}
      <AnalysisChartGallery figures={analysis.figures} />
      <WarningList warnings={analysis.warnings} />
    </AgentDisclosure>
  );
}

function title(method: string): string {
  return method.replaceAll("_", " ");
}
