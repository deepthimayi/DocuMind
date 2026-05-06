import { useState, useRef, useEffect, useCallback } from "react";
import { Send, RotateCcw } from "lucide-react";
import MessageBubble from "./MessageBubble";

const API = "/api";

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center px-6">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-800 border border-gray-700">
        <span className="text-2xl">💬</span>
      </div>
      <div>
        <p className="text-base font-semibold text-gray-300">Ask anything about your document</p>
        <p className="mt-1 text-sm text-gray-500 max-w-xs">
          Upload a PDF or text file, then type a question. Answers are grounded in your document with source citations.
        </p>
      </div>
      <div className="mt-2 flex flex-wrap justify-center gap-2">
        {["Summarize this document", "What are the key findings?", "Who are the main authors?"].map((hint) => (
          <span key={hint} className="rounded-lg bg-gray-800 px-3 py-1.5 text-xs text-gray-400 border border-gray-700">
            {hint}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ChatWindow({ docId, disabled }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [input]);

  const sendMessage = useCallback(async () => {
    const question = input.trim();
    if (!question || isLoading || !docId) return;

    setInput("");
    setIsLoading(true);

    const userMsg = { role: "user", content: question, id: Date.now() };
    const assistantMsg = { role: "assistant", content: "", streaming: true, sources: [], id: Date.now() + 1 };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    // Build history from current messages (before this turn)
    const history = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: docId, question, history }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Server error" }));
        throw new Error(err.detail || "Request failed");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let sources = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep incomplete line

        for (const line of lines) {
          if (line.startsWith("event: sources")) continue;
          if (line.startsWith("event: done")) continue;
          if (line.startsWith("event: error")) continue;

          if (line.startsWith("data: ")) {
            const raw = line.slice(6);

            if (raw === "[DONE]") continue;

            // Try to parse as sources JSON
            try {
              const parsed = JSON.parse(raw);
              if (Array.isArray(parsed)) {
                sources = parsed;
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantMsg.id ? { ...m, sources } : m))
                );
                continue;
              }
            } catch (_) {}

            // Regular token — unescape newlines
            const token = raw.replace(/\\n/g, "\n");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id ? { ...m, content: m.content + token } : m
              )
            );
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? { ...m, content: "", streaming: false, error: err.message }
            : m
        )
      );
    } finally {
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantMsg.id ? { ...m, streaming: false } : m))
      );
      setIsLoading(false);
    }
  }, [input, isLoading, docId, messages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-6">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="mx-auto max-w-2xl space-y-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-800 bg-gray-950 px-4 py-4">
        <div className="mx-auto max-w-2xl">
          {messages.length > 0 && (
            <div className="mb-2 flex justify-end">
              <button
                onClick={() => setMessages([])}
                className="flex items-center gap-1 text-xs text-gray-600 hover:text-gray-400 transition-colors"
              >
                <RotateCcw className="h-3 w-3" />
                Clear chat
              </button>
            </div>
          )}
          <div
            className={`
              flex items-end gap-3 rounded-xl border bg-gray-900 px-4 py-3 transition-colors
              ${disabled ? "border-gray-800 opacity-50" : "border-gray-700 focus-within:border-brand-600"}
            `}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={disabled ? "Upload a document to start chatting…" : "Ask a question about your document…"}
              disabled={disabled || isLoading}
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm text-gray-100 placeholder-gray-600 outline-none disabled:cursor-not-allowed"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading || disabled}
              className={`
                flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-lg transition-all
                ${!input.trim() || isLoading || disabled
                  ? "bg-gray-800 text-gray-600 cursor-not-allowed"
                  : "bg-brand-600 text-white hover:bg-brand-500 active:scale-95"
                }
              `}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-gray-700">
            Press <kbd className="font-mono">Enter</kbd> to send · <kbd className="font-mono">Shift+Enter</kbd> for newline
          </p>
        </div>
      </div>
    </div>
  );
}
