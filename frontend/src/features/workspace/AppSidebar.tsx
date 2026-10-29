import { PanelLeftClose, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { AgentMark } from "@/features/workspace/AgentMark";

type AppSidebarProps = {
  onClose?: () => void;
  onNewAnalysis: () => void;
};

export function AppSidebar({
  onClose,
  onNewAnalysis,
}: AppSidebarProps) {
  return (
    <aside className="hidden w-[260px] shrink-0 flex-col border-r border-border/40 bg-sidebar p-3 lg:flex">
      <div className="flex h-11 items-center gap-2.5 px-2">
        <AgentMark compact />
        <span className="min-w-0 flex-1 text-base font-semibold">Data Analysis Planner</span>
        {onClose && (
          <Button aria-label="Close sidebar" title="Close sidebar" variant="ghost" size="icon" onClick={onClose} aria-controls="workspace-sidebar" aria-expanded={true}>
            <PanelLeftClose className="size-4" />
          </Button>
        )}
      </div>

      <Button
        className="mt-3 w-full justify-start"
        onClick={onNewAnalysis}
        size="sm"
        type="button"
        variant="ghost"
      >
        <Plus className="size-4" />
        New analysis
      </Button>

      <nav aria-label="Recent analyses" className="mt-5">
        <p className="px-3 text-sm font-medium text-muted-foreground">
          Recent
        </p>
        <p className="mt-2 px-3 text-sm leading-6 text-muted-foreground">
          No saved analyses yet.
        </p>
      </nav>

      <div className="mt-auto flex items-center gap-2.5 rounded-lg p-2">
        <div
          aria-hidden="true"
          className="grid size-8 place-items-center rounded-full bg-[#d8c7b8] text-sm font-semibold text-[#352b25]"
        >
          WS
        </div>
        <div>
          <p className="text-sm font-medium">Your workspace</p>
          <p className="text-sm text-muted-foreground">Local prototype</p>
        </div>
      </div>
    </aside>
  );
}
