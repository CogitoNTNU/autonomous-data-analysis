import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownText({ text }: { text: string }) {
  return (
    <div className="markdown-body min-w-0 text-base leading-7">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        disallowedElements={["img"]}
        components={{
          table: ({ children }) => (
            <div className="max-w-full overflow-x-auto" role="region" aria-label="Scrollable table" tabIndex={0}>
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {text}
      </Markdown>
    </div>
  );
}
