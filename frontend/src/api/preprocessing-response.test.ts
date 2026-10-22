import { describe, expect, it } from "vitest";

import { mapPreprocessingPayload } from "@/api/preprocessing-response";

describe("mapPreprocessingPayload", () => {
  it("maps the preprocessing report", () => {
    const result = mapPreprocessingPayload({
      status: "success",
      report: {
        changes: ["drop_missing (handle_missing_values): Dropped 1 row"],
        affected_columns: ["age"],
        rows_before: 2,
        rows_after: 1,
        warnings: [{ message: "One row was removed." }],
      },
    });

    expect(result).toEqual({
      status: "report",
      report: {
        changes: ["drop_missing (handle_missing_values): Dropped 1 row"],
        affectedColumns: ["age"],
        rowsBefore: 2,
        rowsAfter: 1,
        warnings: ["One row was removed."],
      },
    });
  });

  it("rejects a report without row counts", () => {
    expect(() =>
      mapPreprocessingPayload({
        status: "success",
        report: { changes: [], rows_before: 1 },
      }),
    ).toThrow("no row count");
  });

  it("keeps an execution error as a message", () => {
    const result = mapPreprocessingPayload({
      status: "error",
      message: "Unknown preprocessing tool: invent_column",
    });

    expect(result).toEqual({
      status: "error",
      message: "Unknown preprocessing tool: invent_column",
    });
  });
});