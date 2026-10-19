import { ChevronDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AgentMark } from "@/features/workspace/AgentMark";

type WorkspaceHeaderProps = {
  datasetName?: string;
};

export function WorkspaceHeader({ datasetName }: WorkspaceHeaderProps) {
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
      </div>
    </header>
  );
}
