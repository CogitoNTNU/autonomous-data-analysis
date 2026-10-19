import { describe, expect, it } from "vitest";

import {
  parseCsvRows,
  readCsvPreview,
} from "@/features/dataset-upload/read-csv-preview";

describe("readCsvPreview", () => {
  it("creates typed preview metadata without changing the source file", async () => {
    const csv = "species,mass\nAdelie,3700\nGentoo,5000\n";
    const file = new File([csv], "penguins.csv", { type: "text/csv" });
    const originalSize = file.size;

    const preview = await readCsvPreview(file);

    expect(preview).toMatchObject({
      fileName: "penguins.csv",
      rowCount: 2,
      columnCount: 2,
      columns: ["species", "mass"],
    });
    expect(file.name).toBe("penguins.csv");
    expect(file.size).toBe(originalSize);
  });

  it("rejects a header containing an unnamed column", async () => {
    const file = new File(["species,\nAdelie,3700"], "invalid.csv", {
      type: "text/csv",
    });

    await expect(readCsvPreview(file)).rejects.toThrow(
      "Every CSV column must have a name.",
    );
  });

  it("keeps commas and line breaks inside quoted values", () => {
    expect(parseCsvRows('name,note\nAda,"first, second"\nBob,"two\nlines"')).toEqual([
      ["name", "note"],
      ["Ada", "first, second"],
      ["Bob", "two\nlines"],
    ]);
  });
});
