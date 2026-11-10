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

  it("preserves spaces in column identifiers", async () => {
    const file = new File([" species , mass\nAdelie,3700"], "spaces.csv", { type: "text/csv" });

    const preview = await readCsvPreview(file);

    expect(preview.columns).toEqual([" species ", " mass"]);
    expect(preview.rows).toEqual([["Adelie", "3700"]]);
  });

  it("rejects whitespace-only column names", async () => {
    const file = new File(["species,   \nAdelie,3700"], "unnamed.csv", { type: "text/csv" });

    await expect(readCsvPreview(file)).rejects.toThrow("Every CSV column must have a name.");
  });

  it("rejects duplicate column identifiers", async () => {
    const file = new File(["mass,mass\n3700,5000"], "duplicate.csv", { type: "text/csv" });

    await expect(readCsvPreview(file)).rejects.toThrow("Every CSV column must have a unique name.");
  });

  it("keeps distinct column identifiers that differ in spaces", async () => {
    const file = new File(["mass, mass\n3700,5000"], "distinct.csv", { type: "text/csv" });

    expect((await readCsvPreview(file)).columns).toEqual(["mass", " mass"]);
  });

  it.each([
    ["too few", "species,mass\nAdelie"],
    ["too many", "species,mass\nAdelie,3700,extra"],
    ["too few empty", "species,mass,note\n,"],
  ])("rejects data rows containing %s values", async (_description, csv) => {
    const file = new File([csv], "uneven.csv", { type: "text/csv" });

    await expect(readCsvPreview(file)).rejects.toThrow("Every CSV data row must have the same number of values as the header.");
  });

  it("previews valid quoted multiline fields and explicit empty records", async () => {
    const file = new File(['name,note\nAda,"first, second\nthird"\n,\n\nBob,""\n'], "quoted.csv", { type: "text/csv" });

    const preview = await readCsvPreview(file);

    expect(preview.rowCount).toBe(3);
    expect(preview.rows).toEqual([["Ada", "first, second\nthird"], ["", ""], ["Bob", ""]]);
  });

  it("retains quoted empty records for a one-column CSV", async () => {
    const file = new File(['name\n""\nAda\n'], "empty.csv", { type: "text/csv" });

    expect((await readCsvPreview(file)).rows).toEqual([[""], ["Ada"]]);
  });

  it("skips physical whitespace lines while retaining quoted whitespace values", async () => {
    const file = new File(['name\n   \n"   "\nAda\n'], "whitespace.csv", { type: "text/csv" });

    expect((await readCsvPreview(file)).rows).toEqual([["   "], ["Ada"]]);
  });

  it("keeps commas and line breaks inside quoted values", () => {
    expect(parseCsvRows('name,note\nAda,"first, second"\nBob,"two\nlines"')).toEqual([
      ["name", "note"],
      ["Ada", "first, second"],
      ["Bob", "two\nlines"],
    ]);
  });

  it("preserves quote characters inside unquoted values", () => {
    expect(parseCsvRows('name,note\nAda,6" tall')).toEqual([["name", "note"], ["Ada", '6" tall']]);
  });

  it("rejects text after a quoted value", () => {
    expect(() => parseCsvRows('name,note\nAda,"quoted"extra')).toThrow("invalid text after a quoted value");
  });

  it("preserves escaped quotes inside quoted values", () => {
    expect(parseCsvRows('name,note\nAda,"said ""hello"""')).toEqual([["name", "note"], ["Ada", 'said "hello"']]);
  });
});
