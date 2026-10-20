"use client";

import React, { useState } from "react";
import {
  X,
  FolderPlus,
  ShieldCheck,
  CheckCircle2,
  FileCode,
  Folder,
  Loader2,
  ExternalLink,
  Terminal,
} from "lucide-react";
import { API_BASE } from "@/lib/api";

interface FilePayload {
  filename: string;
  content: string;
}

interface SaveProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultFolderName?: string;
  files: FilePayload[];
  onProjectCreated?: (data: any) => void;
}

export const SaveProjectModal: React.FC<SaveProjectModalProps> = ({
  isOpen,
  onClose,
  defaultFolderName = "mrpl_web_app",
  files,
  onProjectCreated,
}) => {
  const [folderName, setFolderName] = useState(defaultFolderName);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/files/write-project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder_name: folderName,
          files: files,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to create project files");
      }

      const data = await res.json();
      setResult(data);
      if (onProjectCreated) onProjectCreated(data);
    } catch (err: any) {
      setError(err?.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-slate-950 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-slate-900/90 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
                <span>Autonomous Workspace Agent</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Mini Antigravity
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">Permission-based local filesystem deployment</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {result ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300">
                <div className="flex items-center space-x-2 font-semibold text-sm text-emerald-400">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                  <span>Project Created Successfully!</span>
                </div>
                <p className="text-xs text-slate-300 mt-2">
                  All files have been written directly to your local workstation.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5 text-xs">
                <div className="text-slate-400 font-mono text-[11px]">TARGET DIRECTORY:</div>
                <div className="font-mono text-emerald-400 break-all bg-slate-950 p-2 rounded border border-slate-800/80">
                  {result.target_dir}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="text-xs font-medium text-slate-300">Files Written ({result.files?.length || 0}):</div>
                <div className="max-h-36 overflow-y-auto space-y-1">
                  {result.files?.map((f: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono"
                    >
                      <span className="text-slate-200 flex items-center gap-1.5">
                        <FileCode className="w-3.5 h-3.5 text-blue-400" />
                        {f.filename}
                      </span>
                      <span className="text-slate-400 text-[10px]">{f.size} B</span>
                    </div>
                  ))}
                </div>
              </div>

              {result.preview_url && (
                <div className="pt-2">
                  <a
                    href={result.preview_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-lg shadow-emerald-600/20 transition cursor-pointer"
                  >
                    <span>Open Live Browser Preview</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-slate-900 border border-blue-500/20 text-xs text-slate-300 flex items-start space-x-2.5">
                <ShieldCheck className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">Permission Required:</span> The AI agent wants to create a new folder and write the generated code directly to your local computer.
                </div>
              </div>

              {/* Folder Name Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <Folder className="w-3.5 h-3.5 text-blue-400" />
                  <span>Project Folder Name:</span>
                </label>
                <input
                  type="text"
                  value={folderName}
                  onChange={(e) => setFolderName(e.target.value)}
                  placeholder="e.g. mrpl_website"
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[10px] text-slate-400">
                  Target: <span className="font-mono text-slate-300">backend/workspace/projects/{folderName || "..."}</span>
                </p>
              </div>

              {/* Files preview list */}
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-slate-300">Files to be generated ({files.length}):</div>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {files.map((f, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono"
                    >
                      <span className="text-slate-300 flex items-center gap-1.5">
                        <FileCode className="w-3.5 h-3.5 text-blue-400" />
                        {f.filename}
                      </span>
                      <span className="text-slate-400 text-[10px]">{f.content.length} chars</span>
                    </div>
                  ))}
                </div>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs">
                  {error}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 bg-slate-900/80 border-t border-slate-800 flex items-center justify-end space-x-2">
          {result ? (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition cursor-pointer"
            >
              Close
            </button>
          ) : (
            <>
              <button
                onClick={onClose}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-700 text-xs font-medium transition cursor-pointer"
              >
                Deny / Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading || !folderName.trim()}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shadow-lg shadow-blue-600/20 transition cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Writing Files...</span>
                  </>
                ) : (
                  <>
                    <FolderPlus className="w-3.5 h-3.5" />
                    <span>Approve &amp; Write Files</span>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
