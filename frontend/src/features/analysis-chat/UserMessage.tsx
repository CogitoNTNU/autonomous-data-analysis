export function UserMessage({ text }: { text: string }) {
  return (
    <div className="mt-8 flex justify-end sm:mt-10">
      <p className="max-w-[85%] whitespace-pre-line rounded-3xl bg-secondary px-5 py-3 text-base leading-7 text-secondary-foreground sm:max-w-[75%]">
        {text}
      </p>
    </div>
  );
}
