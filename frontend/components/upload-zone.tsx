"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud, FileText, X, CheckCircle2, XCircle, Loader2, RefreshCw } from "lucide-react";
import { documentsApi, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const ALLOWED_EXTENSIONS = [
  "pdf",
  "png",
  "jpg",
  "jpeg",
  "tiff",
  "tif",
  "bmp",
  "gif",
  "webp",
  "docx",
  "doc",
  "txt",
  "md",
  "rtf",
];

export const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB, mirrors backend default

type FileState =
  | "selected"
  | "uploading"
  | "accepted"
  | "failed";

interface Item {
  file: File;
  state: FileState;
  message?: string;
}

interface UploadProps {
  onUploaded?: (documentId: string) => void;
  multi?: boolean;
  buttonLabel?: string;
}

function validateFile(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `Unsupported type “${ext ? ext.toUpperCase() : "?"}”. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}.`;
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return "File exceeds the 50 MB limit.";
  }
  if (file.size === 0) {
    return "File is empty.";
  }
  return null;
}

export function UploadZone({
  onUploaded,
  multi = false,
  buttonLabel = "Select files",
}: UploadProps) {
  const { toast } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const addFiles = useCallback(
    (list: FileList | File[] | null) => {
      if (!list) return;
      const arr = Array.from(list);
      const merged: File[] = multi ? [...items.map((i) => i.file), ...arr] : arr;
      setItems(
        merged.map((file) => {
          const error = validateFile(file);
          return { file, state: error ? ("failed" as const) : ("selected" as const), message: error ?? undefined };
        })
      );
    },
    [multi] // eslint-disable-line react-hooks/exhaustive-deps
  );

  async function handleUpload() {
    const pending = items.filter((i) => i.state === "selected");
    if (!pending.length || uploading) return;
    setUploading(true);
    const ids: string[] = [];
    try {
      for (let idx = 0; idx < pending.length; idx++) {
        const item = pending[idx];
        setItems((prev) =>
          prev.map((i) =>
            i.file === item.file ? { ...i, state: "uploading" as const, message: undefined } : i
          )
        );
        try {
          const task = await documentsApi.upload(item.file);
          ids.push(task.document_id);
          setItems((prev) =>
            prev.map((i) =>
              i.file === item.file
                ? { ...i, state: "accepted" as const, message: `Queued · will process shortly` }
                : i
            )
          );
          onUploaded?.(task.document_id);
        } catch (err) {
          const message = err instanceof ApiError ? err.message : "Upload failed";
          setItems((prev) =>
            prev.map((i) =>
              i.file === item.file ? { ...i, state: "failed" as const, message } : i
            )
          );
        }
      }
      const ok = ids.length;
      toast(
        ok > 0 ? "success" : "error",
        ok > 0
          ? `Uploaded ${ok} file(s). Processing started in the background.`
          : "None of the files could be uploaded."
      );
    } finally {
      setUploading(false);
    }
  }

  function removeItem(target: File) {
    setItems((prev) => prev.filter((i) => i.file !== target));
  }

  function resetFailed() {
    setItems((prev) =>
      prev.map((i) => (i.state === "failed" ? { ...i, state: "selected", message: undefined } : i))
    );
  }

  const hasSelected = items.some((i) => i.state === "selected");
  const hasFailed = items.some((i) => i.state === "failed");

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!uploading) addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        aria-label="Upload documents"
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed bg-card/60 px-6 py-10 text-center transition-[border-color,background-color,transform] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          dragging
            ? "border-primary/60 bg-primary/5"
            : "border-border hover:border-primary/40 hover:bg-card"
        )}
      >
        <div
          className={cn(
            "mb-3 flex size-12 items-center justify-center rounded-full border bg-muted/50 text-muted-foreground transition-transform duration-200",
            dragging && "scale-110 text-primary"
          )}
        >
          <UploadCloud className="size-5" />
        </div>
        <p className="text-sm font-medium text-foreground">
          {dragging ? "Drop to upload" : "Drag & drop files here, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          PDF, PNG, JPG, TIFF, DOCX, TXT, MD, RTF — up to 50 MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple={multi}
          className="hidden"
          accept={ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",")}
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {items.length > 0 && (
        <ul className="space-y-2" aria-live="polite">
          {items.map((item) => (
            <li
              key={item.file.name + item.file.size}
              className={cn(
                "flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-sm shadow-sm",
                item.state === "failed" && "border-red-200 bg-red-50/40 dark:border-red-900"
              )}
            >
              <FileText className="size-4 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate font-medium text-foreground">
                {item.file.name}
              </span>

              {item.state === "selected" && (
                <span className="text-xs text-muted-foreground">
                  {(item.file.size / 1024).toFixed(1)} KB
                </span>
              )}
              {item.state === "uploading" && (
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Loader2 className="size-3.5 animate-spin-slow" />
                  Uploading…
                </span>
              )}
              {item.state === "accepted" && (
                <span className="flex items-center gap-1.5 text-xs text-emerald-600">
                  <CheckCircle2 className="size-3.5" />
                  Queued
                </span>
              )}
              {item.state === "failed" && (
                <span className="flex items-center gap-1.5 text-xs text-red-600" title={item.message}>
                  <XCircle className="size-3.5 shrink-0" />
                  <span className="max-w-[220px] truncate">{item.message}</span>
                </span>
              )}

              {item.state !== "uploading" && (
                <button
                  type="button"
                  aria-label={`Remove ${item.file.name}`}
                  onClick={() => removeItem(item.file)}
                  className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button
          onClick={handleUpload}
          disabled={!hasSelected || uploading}
          variant={hasSelected ? "default" : "outline"}
        >
          {uploading ? "Uploading…" : hasSelected ? buttonLabel : "Nothing to upload"}
        </Button>
        {hasFailed && (
          <Button variant="outline" size="sm" onClick={resetFailed}>
            <RefreshCw />
            Retry failed
          </Button>
        )}
        {items.some((i) => i.state === "accepted") && (
          <span className="text-xs text-muted-foreground">
            Files are queued — your dashboard will update automatically.
          </span>
        )}
      </div>
    </div>
  );
}