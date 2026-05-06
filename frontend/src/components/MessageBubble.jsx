import { User, Bot, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { useState } from "react";

function SourceBadge({ source, index }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-gray-800 px-2 py-0.5 text-xs font-mono text-gray-400 border border-gray-700">
      <ExternalLink className="h-3 w-3 text-brand-400" />
      <span className="text-brand-400">#{index + 1}</span>
      <span className="text-gray-500 truncate max-w-[140px]">{source.filename}</span>
      <span className="text-gray-600">·</span>
      <span className="text-gray-500">{Math.round(source.relevance_score * 100)}%</span>
    </span>
  );
}

function SourcesPanel({ sources }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3 rounded-lg border border-gray-800 bg-gray-900/50 text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-gray-400 hover:text-gray-200 transition-colors"
      >
        <span className="font-medium">
          {sources.length} source{sources.length !== 1 ? "s" : ""} retrieved
        </span>
        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {open && (
        <div className="border-t border-gray-800 px-3 pb-3 pt-2 space-y-1.5 animate-fade-in">
          {sources.map((src, i) => (
            <SourceBadge key={i} source={src} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-end gap-0.5 h-4">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="inline-block h-1.5 w-1.5 rounded-full bg-gray-500 animate-bounce"
          style={{ animationDelay: `${i * 150}ms`, animationDuration: "1s" }}
        />
      ))}
    </span>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const isStreaming = message.streaming;

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`
          flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-full
          ${isUser ? "bg-brand-600" : "bg-gray-800 border border-gray-700"}
        `}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-brand-400" />
        )}
      </div>

      {/* Bubble */}
      <div className={`flex max-w-[80%] flex-col ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`
            rounded-2xl px-4 py-2.5 text-sm leading-relaxed
            ${isUser
              ? "bg-brand-600 text-white rounded-tr-sm"
              : "bg-gray-800 text-gray-100 rounded-tl-sm border border-gray-700/50"
            }
          `}
        >
          {message.content ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : isStreaming ? (
            <TypingDots />
          ) : null}
          {isStreaming && message.content && (
            <span className="ml-1 inline-block h-3.5 w-0.5 bg-brand-400 animate-pulse align-middle" />
          )}
        </div>

        {/* Sources panel — only on assistant messages with sources */}
        {!isUser && message.sources && message.sources.length > 0 && !isStreaming && (
          <div className="w-full">
            <SourcesPanel sources={message.sources} />
          </div>
        )}

        {/* Error state */}
        {message.error && (
          <p className="mt-1 text-xs text-red-400">{message.error}</p>
        )}
      </div>
    </div>
  );
}
