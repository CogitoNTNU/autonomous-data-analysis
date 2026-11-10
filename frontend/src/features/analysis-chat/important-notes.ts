export type ImportantNotesView = {
  notes: string[];
  details: string[];
};

const detailCodes = new Set([
  "CONSTANT_COLUMN", "INSUFFICIENT_DATA", "MISSING_GROUP_VALUES",
]);

export function importantNotes(limitations: string[]): ImportantNotesView {
  const notes: string[] = [];
  const details: string[] = [];
  const codes = new Set<string>();
  const seen = new Set<string>();

  for (const limitation of limitations) {
    const text = limitation.trim();
    const key = text.replace(/\s+/g, " ");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    const diagnostic = /^([A-Z][A-Z0-9_]*) \([^()\n]+\):\s*\S/.exec(text);
    const code = diagnostic?.[1];
    const partial = /^Result '[^'\n]+' is partial; its warnings must accompany any findings\.$/.test(text);
    if ((code && detailCodes.has(code)) || partial) {
      details.push(text);
      if (code) codes.add(code);
    } else {
      // Unknown warnings and ordinary qualifications stay visible.
      notes.push(text);
    }
  }

  if (notes.length === 0 && details.length > 0) {
    if (codes.has("CONSTANT_COLUMN")) {
      notes.push("Some columns are constant and cannot support correlation calculations.");
    }
    if (codes.has("INSUFFICIENT_DATA")) {
      notes.push("Some calculations are undefined because there are too few usable observations or insufficient variation. See technical details for the affected columns and pairs.");
    }
    if (codes.has("MISSING_GROUP_VALUES")) {
      notes.push("Some grouping labels are missing and were retained as null groups.");
    }
    if (notes.length === 0) {
      notes.push("Some analysis results are partial. See technical details for their recorded limitations.");
    }
  }
  return { notes, details };
}
