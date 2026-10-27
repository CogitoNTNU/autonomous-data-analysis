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
    <div className="mt-3">
      <p className="text-[10px] font-semibold">{heading}</p>
      <ul className="mt-1.5 space-y-1.5 text-[11px] leading-4 text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
