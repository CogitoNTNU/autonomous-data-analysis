import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CONVERSATION_STORAGE_KEY } from "./constants";
import {
  ConversationHarness,
  dayMs,
  memoryStore,
  startedAt,
  userMessage,
} from "./conversation.fixture";

describe("samtalen varer i 24 timer", () => {
  it("beholder samtalen til fristen og fjerner den når fristen er nådd", () => {
    const store = memoryStore();
    const first = render(
      <ConversationHarness
        draft={userMessage}
        now={() => startedAt}
        store={store}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    first.unmount();

    const justBefore = new Date(startedAt.getTime() + dayMs - 1);
    const stillOpen = render(
      <ConversationHarness
        draft={userMessage}
        now={() => justBefore}
        store={store}
      />,
    );
    expect(screen.getByText(userMessage.content)).toBeTruthy();
    stillOpen.unmount();

    const deadline = new Date(startedAt.getTime() + dayMs);
    render(
      <ConversationHarness
        draft={userMessage}
        now={() => deadline}
        store={store}
      />,
    );
    expect(screen.getByText("Ingen samtale")).toBeTruthy();
    expect(store.getItem(CONVERSATION_STORAGE_KEY)).toBeNull();
  });
});
