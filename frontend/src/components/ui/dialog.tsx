import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { ComponentPropsWithoutRef } from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogTitle = DialogPrimitive.Title;

export function DialogContent({ children, className, ...props }: ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
      <DialogPrimitive.Content
        aria-describedby={undefined}
        className={cn("fixed inset-0 z-50 flex items-center justify-center p-4 pt-16 outline-none sm:p-12 sm:pt-20", className)}
        {...props}
      >
        {children}
        <DialogPrimitive.Close asChild>
          <Button aria-label="Close chart" title="Close chart" variant="ghost" size="icon" className="absolute right-4 top-4 rounded-full bg-black/40 text-white hover:bg-white/20 hover:text-white focus-visible:ring-white sm:right-6 sm:top-6">
            <X aria-hidden="true" className="size-5" />
          </Button>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
