import { Moon, PanelLeftOpen, Plus, Sun } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AgentMark } from "@/features/workspace/AgentMark";
import type { Theme } from "@/features/workspace/use-theme";

type WorkspaceHeaderProps = {
  datasetName?: string;
  hasDataset: boolean;
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  onNewAnalysis: () => void;
  onToggleTheme: () => void;
  theme: Theme;
};

export function WorkspaceHeader({
  datasetName,
  hasDataset,
  sidebarOpen = true,
  onToggleSidebar,
  onNewAnalysis,
  onToggleTheme,
  theme,
}: WorkspaceHeaderProps) {
  const nextTheme = theme === "light" ? "dark" : "light";

  return (
    <header className="flex h-14 shrink-0 items-center border-b border-border bg-background/95 px-4 backdrop-blur sm:px-5">
      {!sidebarOpen && onToggleSidebar && (
        <Button className="mr-2 hidden lg:inline-flex" aria-label="Open sidebar" title="Open sidebar" variant="ghost" size="icon" onClick={onToggleSidebar} aria-controls="workspace-sidebar" aria-expanded={false}>
          <PanelLeftOpen className="size-4" />
        </Button>
      )}
      <AgentMark className="mr-2 lg:hidden" compact />
      <div className="px-2 text-sm font-medium">
        Planner <span className="font-normal text-muted-foreground">v1</span>
      </div>
      {datasetName && (
        <Badge
          className="ml-2 hidden max-w-48 truncate text-[9px] font-normal sm:inline-flex"
          variant="secondary"
        >
          {datasetName}
        </Badge>
      )}
      <div className="ml-auto flex items-center gap-2 text-[10px] text-muted-foreground">
        <span className="size-1.5 rounded-full bg-emerald-600" />
        <span className="hidden sm:inline">Planning mode</span>
        {hasDataset && (
          <Button
            aria-label="Start new analysis"
            className="ml-1 lg:hidden"
            onClick={onNewAnalysis}
            size="icon"
            title="Start new analysis"
            type="button"
            variant="ghost"
          >
            <Plus className="size-4" />
          </Button>
        )}
        <Button
          aria-label={`Switch to ${nextTheme} mode`}
          className="ml-1"
          onClick={onToggleTheme}
          size="icon"
          title={`Switch to ${nextTheme} mode`}
          type="button"
          variant="ghost"
        >
          {theme === "light" ? (
            <Moon className="size-4" />
          ) : (
            <Sun className="size-4" />
          )}
        </Button>
      </div>
    </header>
  );
}
