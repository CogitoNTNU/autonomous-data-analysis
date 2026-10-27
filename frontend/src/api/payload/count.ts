export function count(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${name} returned an unreadable response`);
  }
  return value;
}
