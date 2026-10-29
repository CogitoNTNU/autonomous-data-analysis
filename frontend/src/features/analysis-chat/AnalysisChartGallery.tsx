import { AnalysisChart } from "@/features/analysis-chat/AnalysisChart";
import type { AnalysisFigure } from "@/types/planner";

export function AnalysisChartGallery({
  figures,
  figureIds = figures.map((figure) => figure.id),
}: {
  figures: AnalysisFigure[];
  figureIds?: string[];
}) {
  const ids = [...new Set(figureIds)];
  if (ids.length === 0) return null;

  return (
    <div aria-label="Analysis charts" className="mt-6 grid grid-cols-[repeat(auto-fit,minmax(min(100%,280px),1fr))] items-start gap-4" role="group">
      {ids.map((id, index) => {
        const figure = figures.find((item) => item.id === id);
        if (!figure?.image.trim()) {
          return <p key={id} className="text-base leading-7 text-muted-foreground">This chart could not be loaded</p>;
        }
        return (
          <AnalysisChart
            key={id}
            figure={figure}
            label={ids.length === 1 ? "Analysis chart" : `Analysis chart ${index + 1}`}
          />
        );
      })}
    </div>
  );
}
