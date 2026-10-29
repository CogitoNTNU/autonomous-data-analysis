import { useId, useState, type ReactNode } from "react";
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
  const detailsId = useId();

  return (
    <section>
      <AgentTurn agent={agent} compact>
        <Button
          variant="ghost"
          aria-label={summary}
          aria-controls={detailsId}
          aria-expanded={open}
          className="flex h-auto w-full items-center gap-3 whitespace-normal rounded-md px-0 py-1 text-left text-base font-medium leading-7 hover:bg-transparent hover:text-muted-foreground"
          onClick={() => setOpen((current) => !current)}
          type="button"
        >
          <span className="min-w-0 flex-1">{summary}</span>
          {statusBadge}
          <ChevronRight
            aria-hidden="true"
            className={cn(
              "size-4 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-90",
            )}
          />
        </Button>
        {open && (
          <div className="mt-3" id={detailsId}>
            {detailsTitle ? (
              <Card className="overflow-hidden shadow-none">
                <CardHeader className="border-b p-4">
                  <CardTitle className="text-xl font-semibold leading-7 tracking-tight">{detailsTitle}</CardTitle>
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
