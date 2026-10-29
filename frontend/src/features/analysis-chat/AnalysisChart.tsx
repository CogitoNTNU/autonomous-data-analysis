import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { AnalysisFigure } from "@/types/planner";

type AnalysisChartProps = {
  figure: AnalysisFigure;
  label: string;
};

export function AnalysisChart({ figure, label }: AnalysisChartProps) {
  return (
    <figure className="w-full max-w-[440px] min-w-0">
      <Dialog>
        <DialogTrigger asChild>
          <Button
            variant="ghost"
            aria-label={`Enlarge ${label.toLowerCase()}`}
            title="Click to enlarge"
            className="group relative flex aspect-[4/3] h-auto w-full cursor-zoom-in overflow-hidden rounded-xl border border-border/60 bg-white p-2 hover:bg-white focus-visible:ring-2"
          >
            <img alt={label} className="block h-full w-full object-contain" src={figure.image} loading="lazy" />
            <span aria-hidden="true" className="pointer-events-none absolute inset-0 bg-black/0 transition-colors duration-200 group-hover:bg-black/15 group-focus-visible:bg-black/15" />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle className="sr-only">{label}</DialogTitle>
          <img alt={label} src={figure.image} className="block h-auto max-h-full w-auto max-w-full rounded-lg object-contain shadow-2xl" />
        </DialogContent>
      </Dialog>
    </figure>
  );
}
