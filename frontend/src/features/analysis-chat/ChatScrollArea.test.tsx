import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatScrollArea } from "@/features/analysis-chat/ChatScrollArea";

describe("ChatScrollArea", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("hides the arrow at the top", () => {
    render(<ChatScrollArea>Conversation content</ChatScrollArea>);
    expect(screen.queryByRole("button", { name: "Back to top" })).toBeNull();
  });

  it("follows new content until the reader scrolls away", () => {
    const { rerender } = render(<ChatScrollArea>One</ChatScrollArea>);
    const viewport = screen.getByRole("region", { name: "Conversation" });
    Object.defineProperty(viewport, "scrollHeight", { configurable: true, value: 500 });
    Object.defineProperty(viewport, "clientHeight", { configurable: true, value: 100 });
    rerender(<ChatScrollArea>One more</ChatScrollArea>);
    expect(viewport.scrollTop).toBe(500);
    viewport.scrollTop = 0;
    fireEvent.scroll(viewport);
    rerender(<ChatScrollArea>One more line</ChatScrollArea>);
    expect(viewport.scrollTop).toBe(0);
  });

  it("scrolls the conversation to the top and hides the arrow after returning", async () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: false }));
    const user = userEvent.setup();
    render(<ChatScrollArea>Conversation content</ChatScrollArea>);
    const viewport = screen.getByRole("region", { name: "Conversation" });
    const scrollTo = vi.fn();
    viewport.scrollTo = scrollTo;
    fireEvent.scroll(viewport, { target: { scrollTop: 300 } });
    await user.click(screen.getByRole("button", { name: "Back to top" }));
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
    fireEvent.scroll(viewport, { target: { scrollTop: 0 } });
    expect(screen.queryByRole("button", { name: "Back to top" })).toBeNull();
  });
});
