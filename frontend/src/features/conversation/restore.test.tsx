import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CONVERSATION_STORAGE_KEY } from "./constants";
import {
  ConversationHarness,
  assistantMessage,
  dayMs,
  memoryStore,
  penguinDataset,
  startedAt,
  userMessage,
} from "./conversation.fixture";

describe("samtalen overlever at nettleseren lukkes", () => {
  it("viser meldingene igjen og beholder fristen fra første melding", () => {
    const store = memoryStore();
    const first = render(
      <ConversationHarness
        draft={userMessage}
        now={() => startedAt}
        store={store}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    const deadline = new Date(startedAt.getTime() + dayMs).toISOString();
    expect(screen.getByText(`Utløper ${deadline}`)).toBeTruthy();
    first.unmount();

    const later = new Date(startedAt.getTime() + 60 * 60 * 1000);
    render(
      <ConversationHarness
        draft={assistantMessage}
        now={() => later}
        store={store}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(screen.getByText(userMessage.content)).toBeTruthy();
    expect(screen.getByText(assistantMessage.content)).toBeTruthy();
    expect(screen.getByText(`Utløper ${deadline}`)).toBeTruthy();

    const saved = JSON.parse(store.getItem(CONVERSATION_STORAGE_KEY) ?? "");
    expect(Object.keys(saved).sort()).toEqual([
      "dataset",
      "expires_at",
      "messages",
    ]);
    expect(saved.dataset).toEqual(penguinDataset);
  });
});
