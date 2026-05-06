import { useState } from "react";
import { BookOpen, Github, Zap } from "lucide-react";
import FileUpload from "./components/FileUpload";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [currentDoc, setCurrentDoc] = useState(null);

  const handleDocumentUploaded = (doc) => {
    setCurrentDoc(doc);
  };

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100 font-sans">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white">RAG Chatbot</h1>
              <p className="text-[10px] text-gray-500 leading-none">Powered by Claude + ChromaDB</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {currentDoc && (
              <div className="hidden sm:flex items-center gap-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1">
                <BookOpen className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-xs text-emerald-400 font-medium truncate max-w-[160px]">
                  {currentDoc.filename}
                </span>
              </div>
            )}
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 rounded-md bg-gray-800 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors border border-gray-700"
            >
              <Github className="h-3.5 w-3.5" />
              Source
            </a>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="hidden lg:flex w-72 flex-shrink-0 flex-col border-r border-gray-800 bg-gray-900/40 p-4 gap-4">
          <div>
            <h2 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Document
            </h2>
            <p className="text-xs text-gray-600 mb-3">
              Upload a PDF or text file to get started
            </p>
            <FileUpload onDocumentUploaded={handleDocumentUploaded} currentDoc={currentDoc} />
          </div>

          {currentDoc && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-3">
              <h3 className="text-xs font-semibold text-gray-400 mb-2">Document info</h3>
              <dl className="space-y-1">
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-600">File</dt>
                  <dd className="text-xs text-gray-300 font-mono truncate max-w-[120px]">{currentDoc.filename}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-600">Chunks</dt>
                  <dd className="text-xs text-gray-300">{currentDoc.chunk_count}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-600">Model</dt>
                  <dd className="text-xs text-gray-300">claude-sonnet-4</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-600">Embeddings</dt>
                  <dd className="text-xs text-gray-300">MiniLM-L6</dd>
                </div>
              </dl>
            </div>
          )}

          <div className="mt-auto rounded-lg border border-gray-800 bg-gray-900/50 p-3">
            <h3 className="text-xs font-semibold text-gray-500 mb-1.5">How it works</h3>
            <ol className="space-y-1.5">
              {[
                "Document is split into 500-char chunks",
                "Chunks are embedded with MiniLM-L6",
                "Your question is embedded + matched",
                "Top 3 chunks sent to Claude as context",
                "Answer streamed back with citations",
              ].map((step, i) => (
                <li key={i} className="flex gap-2 text-xs text-gray-600">
                  <span className="flex-shrink-0 text-brand-600 font-mono">{i + 1}.</span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </aside>

        {/* Mobile upload bar */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 z-10 border-t border-gray-800 bg-gray-950 p-3">
          {!currentDoc && (
            <FileUpload onDocumentUploaded={handleDocumentUploaded} currentDoc={currentDoc} />
          )}
        </div>

        {/* Chat area */}
        <main className="flex-1 overflow-hidden pb-0 lg:pb-0">
          <ChatWindow docId={currentDoc?.doc_id} disabled={!currentDoc} />
        </main>
      </div>
    </div>
  );
}
