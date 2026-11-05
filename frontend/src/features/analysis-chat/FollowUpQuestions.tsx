import { Button } from "@/components/ui/button";

type FollowUpQuestionsProps = {
  questions: string[];
  onSelect: (question: string) => void;
};

export function FollowUpQuestions({ questions, onSelect }: FollowUpQuestionsProps) {
  if (questions.length === 0) return null;
  return (
    <div className="mt-6" role="group" aria-label="Follow-up questions">
      <h3 className="text-lg font-semibold leading-7 tracking-tight">Explore further</h3>
      <div className="mt-2 flex min-w-0 flex-wrap gap-2">
        {questions.map((question) => (
          <Button key={question} className="h-auto max-w-full min-w-0 shrink whitespace-normal break-words rounded-full text-left" onClick={() => onSelect(question)} size="sm" variant="outline">
            {question}
          </Button>
        ))}
      </div>
    </div>
  );
}
