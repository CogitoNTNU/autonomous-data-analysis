import { ArrowUp } from "lucide-react";
import { useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function ChatScrollArea({ children }: { children: ReactNode }) {
  const viewport = useRef<HTMLDivElement>(null);
  const [showBackToTop, setShowBackToTop] = useState(false);

  function backToTop() {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    viewport.current?.scrollTo({ top: 0, behavior: reducedMotion ? "instant" : "smooth" });
  }

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={viewport}
        role="region"
        aria-label="Conversation"
        className="h-full overflow-y-auto px-4 sm:px-16"
        onScroll={(event) => setShowBackToTop(event.currentTarget.scrollTop > 160)}
      >
        {children}
      </div>
      {showBackToTop && (
        <Button
          aria-label="Back to top"
          title="Back to top"
          variant="outline"
          size="icon"
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-background/95 text-foreground shadow-md hover:bg-muted"
          onClick={backToTop}
        >
          <ArrowUp aria-hidden="true" className="size-4" />
        </Button>
      )}
    </div>
  );
}
