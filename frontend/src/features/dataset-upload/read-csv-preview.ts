import type { DatasetPreview } from "@/types/dataset";

const PREVIEW_ROW_LIMIT = 4;

export function readCsvText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.addEventListener("load", () => {
      if (typeof reader.result !== "string") {
        reject(new Error("The CSV could not be read as text."));
        return;
      }

      resolve(reader.result);
    });
    reader.addEventListener("error", () => {
      reject(new Error("The CSV could not be read."));
    });
    reader.readAsText(file);
  });
}

export function parseCsvRows(csv: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let value = "";
  let inQuotes = false;

  for (let index = 0; index < csv.length; index += 1) {
    const character = csv[index];
    const nextCharacter = csv[index + 1];

    if (character === '"') {
      if (inQuotes && nextCharacter === '"') {
        value += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (character === "," && !inQuotes) {
      row.push(value);
      value = "";
      continue;
    }

    if ((character === "\n" || character === "\r") && !inQuotes) {
      if (character === "\r" && nextCharacter === "\n") {
        index += 1;
      }
      row.push(value);
      if (row.some((cell) => cell.trim() !== "")) {
        rows.push(row);
      }
      row = [];
      value = "";
      continue;
    }

    value += character;
  }

  if (inQuotes) {
    throw new Error("The CSV contains an unfinished quoted value.");
  }

  row.push(value);
  if (row.some((cell) => cell.trim() !== "")) {
    rows.push(row);
  }

  return rows;
}

export async function readCsvPreview(file: File): Promise<DatasetPreview> {
  const csv = (await readCsvText(file)).replace(/^\uFEFF/, "");
  const parsedRows = parseCsvRows(csv);
  const [rawColumns, ...dataRows] = parsedRows;

  if (!rawColumns || rawColumns.length === 0) {
    throw new Error("The CSV does not contain a header row.");
  }

  const columns = rawColumns.map((column) => column.trim());
  if (columns.some((column) => column.length === 0)) {
    throw new Error("Every CSV column must have a name.");
  }

  return {
    fileName: file.name,
    fileSize: file.size,
    rowCount: dataRows.length,
    columnCount: columns.length,
    columns,
    rows: dataRows.slice(0, PREVIEW_ROW_LIMIT),
  };
}
