import { useState, useRef, useCallback } from "react";
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

const API = "/api";

export default function FileUpload({ onDocumentUploaded, currentDoc }) {
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef(null);

  const uploadFile = useCallback(
    async (file) => {
      const ext = file.name.split(".").pop().toLowerCase();
      if (!["pdf", "txt"].includes(ext)) {
        setStatus("error");
        setErrorMsg("Only PDF and TXT files are supported.");
        return;
      }

      setStatus("uploading");
      setErrorMsg("");

      const form = new FormData();
      form.append("file", file);

      try {
        const res = await fetch(`${API}/upload`, { method: "POST", body: form });
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.detail || "Upload failed.");
        }

        setStatus("success");
        onDocumentUploaded(data);
      } catch (err) {
        setStatus("error");
        setErrorMsg(err.message);
      }
    },
    [onDocumentUploaded]
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
  };

  const reset = () => {
    setStatus("idle");
    setErrorMsg("");
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => status === "idle" && inputRef.current?.click()}
        className={`
          relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
          p-8 transition-all duration-200 cursor-pointer select-none
          ${isDragging
            ? "border-brand-500 bg-brand-500/10"
            : status === "success"
            ? "border-emerald-500/50 bg-emerald-500/5 cursor-default"
            : status === "error"
            ? "border-red-500/50 bg-red-500/5 cursor-default"
            : "border-gray-700 bg-gray-900/50 hover:border-gray-600 hover:bg-gray-900"
          }
        `}
      >
        {status === "uploading" && (
          <>
            <Loader2 className="h-10 w-10 text-brand-400 animate-spin" />
            <p className="text-sm font-medium text-gray-300">Processing document…</p>
            <p className="text-xs text-gray-500">Chunking and indexing, this may take a moment</p>
          </>
        )}

        {status === "success" && currentDoc && (
          <>
            <CheckCircle className="h-10 w-10 text-emerald-400" />
            <div className="text-center">
              <p className="text-sm font-semibold text-emerald-400">Document ready</p>
              <p className="mt-0.5 text-xs text-gray-400 font-mono truncate max-w-[200px]">
                {currentDoc.filename}
              </p>
              <p className="mt-1 text-xs text-gray-500">{currentDoc.chunk_count} chunks indexed</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); reset(); onDocumentUploaded(null); }}
              className="mt-1 text-xs text-gray-500 hover:text-gray-300 underline underline-offset-2 transition-colors"
            >
              Upload a different file
            </button>
          </>
        )}

        {status === "error" && (
          <>
            <AlertCircle className="h-10 w-10 text-red-400" />
            <div className="text-center">
              <p className="text-sm font-semibold text-red-400">Upload failed</p>
              <p className="mt-0.5 text-xs text-gray-400">{errorMsg}</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); reset(); }}
              className="mt-1 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 underline underline-offset-2 transition-colors"
            >
              <X className="h-3 w-3" /> Try again
            </button>
          </>
        )}

        {status === "idle" && (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gray-800">
              <Upload className="h-6 w-6 text-brand-400" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-gray-200">
                Drop your file here, or <span className="text-brand-400">browse</span>
              </p>
              <p className="mt-1 text-xs text-gray-500">PDF or TXT · max 20 MB</p>
            </div>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={handleChange}
          className="hidden"
        />
      </div>
    </div>
  );
}
