import { describe, expect, it } from "vitest";

import {
  readStoredTheme,
  THEME_STORAGE_KEY,
} from "@/features/workspace/use-theme";

describe("readStoredTheme", () => {
  it("restores a saved dark theme", () => {
    const storage = new Map([[THEME_STORAGE_KEY, "dark"]]);

    expect(readStoredTheme({ getItem: (key) => storage.get(key) ?? null })).toBe(
      "dark",
    );
  });

  it("uses light theme for an unsupported stored value", () => {
    expect(readStoredTheme({ getItem: () => "unsupported" })).toBe("light");
  });
});
