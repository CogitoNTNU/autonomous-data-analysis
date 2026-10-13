type NoticeProps = {
  message: string | null;
};

export function ConversationNotice({ message }: NoticeProps) {
  if (message === null) {
    return null;
  }
  return <p role="alert">{message}</p>;
}
