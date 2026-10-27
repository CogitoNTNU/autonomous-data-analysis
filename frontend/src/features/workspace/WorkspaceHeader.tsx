import { Moon, PanelLeftOpen, Plus, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { AgentMark } from "@/features/workspace/AgentMark";
import type { Theme } from "@/features/workspace/use-theme";

type WorkspaceHeaderProps = {
  hasDataset: boolean;
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  onNewAnalysis: () => void;
  onToggleTheme: () => void;
  theme: Theme;
};

export function WorkspaceHeader({
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
      <h1 className="min-w-0 truncate px-2 text-xl font-semibold" title="New chat">
        New chat
      </h1>
      <div className="ml-auto flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
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
          className="ml-1 size-10 rounded-full border border-border text-foreground hover:bg-accent"
          onClick={onToggleTheme}
          size="icon"
          title={`Switch to ${nextTheme} mode`}
          type="button"
          variant="ghost"
        >
          <span aria-hidden="true" className="relative block size-5">
            <Moon
              className={`absolute inset-0 size-5 transition-[transform,opacity] duration-300 ease-in-out ${theme === "light" ? "rotate-0 scale-100 opacity-100" : "-rotate-90 scale-50 opacity-0"}`}
              strokeWidth={2}
            />
            <Sun
              className={`absolute inset-0 size-5 transition-[transform,opacity] duration-300 ease-in-out ${theme === "dark" ? "rotate-0 scale-100 opacity-100" : "rotate-90 scale-50 opacity-0"}`}
              strokeWidth={2}
            />
          </span>
        </Button>
      </div>
    </header>
  );
}
