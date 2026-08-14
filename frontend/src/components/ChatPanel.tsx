import { useEffect, useRef, useState } from "react";
import { api, ChatMessageOut } from "../api/client";

export default function ChatPanel({ reportId }: { reportId: number }) {
  const [messages, setMessages] = useState<ChatMessageOut[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [mode, setMode] = useState<"anthropic" | "offline" | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getChatHistory(reportId).then(setMessages);
    setMessages([]);
  }, [reportId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const question = input.trim();
    if (!question || sending) return;
    setInput("");
    setSending(true);
    setMessages((prev) => [...prev, { role: "user", content: question, created_at: new Date().toISOString() }]);
    try {
      const response = await api.sendChatMessage(reportId, question);
      setMode(response.source);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, created_at: new Date().toISOString() },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: e instanceof Error ? `Error: ${e.message}` : "Something went wrong.",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink-primary dark:text-ink-primary-dark">Ask ESG Copilot</h3>
        {mode && (
          <span className="rounded-full bg-black/5 px-2 py-0.5 text-xs text-ink-muted dark:bg-white/10">
            {mode === "anthropic" ? "Claude-powered" : "Offline mode"}
          </span>
        )}
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-black/10 bg-surface p-3 dark:border-white/10 dark:bg-surface-dark">
        {messages.length === 0 && (
          <p className="text-sm text-ink-muted">
            Ask about this report — e.g. "What are the Scope 1 emissions?" or "How complete is the human rights disclosure?"
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                m.role === "user"
                  ? "bg-series-1 text-white dark:bg-series-1-dark"
                  : "bg-black/5 text-ink-primary dark:bg-white/10 dark:text-ink-primary-dark"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="mt-2 flex gap-2">
        <input
          className="flex-1 rounded-md border border-black/10 bg-surface px-3 py-2 text-sm text-ink-primary outline-none focus:border-series-1 dark:border-white/10 dark:bg-surface-dark dark:text-ink-primary-dark"
          placeholder="Ask a question about this report…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={sending}
        />
        <button
          className="rounded-md bg-series-1 px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 dark:bg-series-1-dark"
          onClick={send}
          disabled={sending || !input.trim()}
        >
          {sending ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
