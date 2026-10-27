export function requiredText(value: unknown, name: string): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${name} left a required field empty`);
  }
  return value;
}
