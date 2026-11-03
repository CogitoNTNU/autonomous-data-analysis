import { AnalysisPlanCard } from "@/features/analysis-chat/AnalysisPlanCard";
import { AnalysisReportCard } from "@/features/analysis-chat/AnalysisReportCard";
import { CriticCard } from "@/features/analysis-chat/CriticCard";
import { InterpretationCard } from "@/features/analysis-chat/InterpretationCard";
import { PreprocessingReportCard } from "@/features/analysis-chat/PreprocessingReportCard";
import type { AnalysisPlan, AnalysisReport, CritiqueView, InterpretationView, PreprocessingReport } from "@/types/planner";

export function AnalysisStages({
  plan,
  report,
  analysis,
  interpretation,
  critique,
  running = false,
}: {
  plan: AnalysisPlan | null;
  report: PreprocessingReport | null;
  analysis: AnalysisReport | null;
  interpretation: InterpretationView | null;
  critique: CritiqueView | null;
  running?: boolean;
}) {
  return (
    <>
      {plan && <AnalysisPlanCard plan={plan} running={running} />}
      {report && <PreprocessingReportCard report={report} />}
      {analysis && <AnalysisReportCard analysis={analysis} />}
      {interpretation && <InterpretationCard interpretation={interpretation} />}
      {critique && <CriticCard critique={critique} />}
    </>
  );
}
