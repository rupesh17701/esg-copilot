import { useRef, useState } from "react";
import { api } from "../api/client";

interface Props {
  onUploaded: (reportId: number) => void;
}

export default function UploadPanel({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const report = await api.uploadReport(file);
      onUploaded(report.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div>
      <label
        className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-baseline p-8 text-center hover:border-series-1 dark:border-baseline-dark"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <span className="text-sm font-medium text-ink-primary dark:text-ink-primary-dark">
          {uploading ? "Processing report…" : "Drop a BRSR report here, or click to choose a file"}
        </span>
        <span className="mt-1 text-xs text-ink-muted">PDF or TXT — parsed, scored, and ready to query in seconds</span>
      </label>
      {error && <p className="mt-2 text-sm text-status-critical">{error}</p>}
    </div>
  );
}
