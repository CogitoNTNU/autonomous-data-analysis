import { ChevronDown, Moon, Sun } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AgentMark } from "@/features/workspace/AgentMark";
import type { Theme } from "@/features/workspace/use-theme";

type WorkspaceHeaderProps = {
  datasetName?: string;
  onToggleTheme: () => void;
  theme: Theme;
};

export function WorkspaceHeader({
  datasetName,
  onToggleTheme,
  theme,
}: WorkspaceHeaderProps) {
  const nextTheme = theme === "light" ? "dark" : "light";

  return (
    <header className="flex h-14 shrink-0 items-center border-b border-border bg-background/95 px-4 backdrop-blur sm:px-5">
      <AgentMark className="mr-2 lg:hidden" compact />
      <Button className="px-2" type="button" variant="ghost">
        Planner <span className="font-normal text-muted-foreground">v1</span>
        <ChevronDown className="size-3.5 text-muted-foreground" />
      </Button>
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
        Planning mode
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
