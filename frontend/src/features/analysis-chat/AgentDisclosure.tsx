import { useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import type { AgentIdentity } from "@/features/analysis-chat/agents";
import { cn } from "@/lib/utils";

type AgentDisclosureProps = {
  agent: AgentIdentity;
  summary: string;
  children: ReactNode;
  actions?: ReactNode;
  defaultOpen?: boolean;
  detailsTitle?: string;
  statusBadge?: ReactNode;
};

export function AgentDisclosure({
  agent,
  summary,
  children,
  actions,
  defaultOpen = false,
  detailsTitle,
  statusBadge,
}: AgentDisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const detailsId = `${agent.initials.toLowerCase()}-details`;

  return (
    <section>
      <AgentTurn agent={agent}>
        <Button
          variant="ghost"
          aria-controls={detailsId}
          aria-expanded={open}
          className="flex h-auto w-full items-center gap-2 rounded-md px-0 py-1 text-left text-base font-medium hover:bg-transparent hover:text-muted-foreground"
          onClick={() => setOpen((current) => !current)}
          type="button"
        >
          <span className="min-w-0 flex-1">{summary}</span>
          {statusBadge}
          <ChevronRight
            className={cn(
              "size-3.5 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-90",
            )}
          />
        </Button>
        {open && (
          <div className="mt-3" id={detailsId}>
            {detailsTitle ? (
              <Card className="overflow-hidden shadow-none">
                <CardHeader className="border-b p-4">
                  <CardTitle className="text-lg">{detailsTitle}</CardTitle>
                </CardHeader>
                <CardContent className="p-4">{children}</CardContent>
              </Card>
            ) : children}
          </div>
        )}
        {actions}
      </AgentTurn>
    </section>
  );
}
