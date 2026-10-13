import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CONVERSATION_STORAGE_KEY } from "./constants";
import {
  ConversationHarness,
  dayMs,
  memoryStore,
  penguinDataset,
  startedAt,
  userMessage,
} from "./conversation.fixture";

describe("ugyldig lagret samtale", () => {
  it("fjerner ødelagt innhold og starter uten historikk", () => {
    const store = memoryStore();
    store.setItem(CONVERSATION_STORAGE_KEY, "{ikke json");

    render(
      <ConversationHarness
        draft={userMessage}
        now={() => startedAt}
        store={store}
      />,
    );

    expect(screen.getByText("Ingen samtale")).toBeTruthy();
    expect(store.getItem(CONVERSATION_STORAGE_KEY)).toBeNull();
  });

  it("avviser en melding uten innhold og skriver ingenting", () => {
    const store = memoryStore();
    render(
      <ConversationHarness
        draft={{ role: "user", content: "  " }}
        now={() => startedAt}
        store={store}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(
      screen.getByRole("alert").textContent,
    ).toBe("Meldingen må ha en rolle og innhold");
    expect(screen.getByText("Ingen samtale")).toBeTruthy();
    expect(store.getItem(CONVERSATION_STORAGE_KEY)).toBeNull();
  });

  it("fjerner et lager som også inneholder analyseresultater", () => {
    const store = memoryStore();
    const expiresAt = new Date(startedAt.getTime() + dayMs).toISOString();
    store.setItem(
      CONVERSATION_STORAGE_KEY,
      JSON.stringify({
        messages: [userMessage],
        dataset: penguinDataset,
        expires_at: expiresAt,
        analysis_results: [{ value: 1 }],
      }),
    );

    render(
      <ConversationHarness
        draft={userMessage}
        now={() => startedAt}
        store={store}
      />,
    );

    expect(screen.getByText("Ingen samtale")).toBeTruthy();
    expect(store.getItem(CONVERSATION_STORAGE_KEY)).toBeNull();
  });
});
