export function TextList({
  items,
  title: heading,
}: {
  items: string[];
  title: string;
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="mt-6">
      <h3 className="text-lg font-semibold leading-7 tracking-tight">{heading}</h3>
      <ul className="mt-2 list-disc space-y-2 pl-5 text-base leading-7 text-foreground/85">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
