import { useId, useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function WorkflowDetails({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <section className="mt-5">
      <Button
        variant="ghost"
        className="gap-2 px-0 text-sm text-muted-foreground hover:bg-transparent hover:text-foreground"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
      >
        <ChevronRight aria-hidden="true" className={cn("size-4 transition-transform", open && "rotate-90")} />
        View analysis details
      </Button>
      {open && <div id={id} className="mt-2 border-t border-border/60 pb-2">{children}</div>}
    </section>
  );
}
