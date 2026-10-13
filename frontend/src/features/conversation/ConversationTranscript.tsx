import type { ConversationMessage } from "../../types/conversation";

type TranscriptProps = {
  messages: ConversationMessage[];
};

export function ConversationTranscript({ messages }: TranscriptProps) {
  if (messages.length === 0) {
    return <p>Ingen samtale</p>;
  }
  return (
    <ol aria-label="Samtale">
      {messages.map((message, index) => (
        <li key={`${index}-${message.role}`}>
          <span>{message.role}</span>
          <p>{message.content}</p>
        </li>
      ))}
    </ol>
  );
}
