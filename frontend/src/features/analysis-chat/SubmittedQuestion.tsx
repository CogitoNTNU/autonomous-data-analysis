import { Check, Copy, Pencil, Upload } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

type SubmittedQuestionProps = {
  question: string;
  onEdit: (question: string) => void;
  editDisabled?: boolean;
};

export function SubmittedQuestion({ question, onEdit, editDisabled }: SubmittedQuestionProps) {
  const [status, setStatus] = useState("");

  async function copy() {
    try {
      await navigator.clipboard.writeText(question);
      setStatus("Copied to clipboard");
    } catch {
      setStatus("Could not copy the message");
    }
  }

  async function share() {
    if (!navigator.share) {
      await copy();
      return;
    }
    try {
      await navigator.share({ text: question });
      setStatus("Message shared");
    } catch (reason: unknown) {
      if (reason instanceof Error && reason.name === "AbortError") return;
      setStatus("Could not share the message");
    }
  }

  return (
    <div className="mt-8 sm:mt-10 flex flex-col items-end">
      <p className="max-w-[85%] rounded-3xl bg-secondary px-5 py-3 text-base leading-7 text-secondary-foreground sm:max-w-[75%]">
        {question}
      </p>
      <div className="mt-1 flex items-center gap-1 text-muted-foreground" role="group" aria-label="Message actions">
        <Button aria-label="Copy message" title="Copy message" variant="ghost" size="icon" onClick={() => void copy()}>
          {status === "Copied to clipboard" ? <Check className="size-4" /> : <Copy className="size-4" />}
        </Button>
        <Button aria-label="Share message" title="Share message" variant="ghost" size="icon" onClick={() => void share()}>
          <Upload className="size-4" />
        </Button>
        <Button aria-label="Edit message" title="Edit message" variant="ghost" size="icon" disabled={editDisabled} onClick={() => onEdit(question)}>
          <Pencil className="size-4" />
        </Button>
      </div>
      <p aria-live="polite" className="text-sm text-muted-foreground">{status}</p>
    </div>
  );
}
