"use client";

import React, { useState } from "react";
import { Download, FileText, FileSpreadsheet, Presentation, Code2, FileCheck, Layers, Eye, Loader2, Trash2, Box, Image as ImageIcon } from "lucide-react";
import { API_BASE, Artifact } from "@/lib/api";
import { LivePreviewModal } from "@/components/LivePreviewModal";

interface ArtifactPanelProps {
  artifacts: Artifact[];
  onDeleteArtifact?: (id: string) => void;
  onClearAll?: () => void;
}

export const ArtifactPanel: React.FC<ArtifactPanelProps> = ({ artifacts, onDeleteArtifact, onClearAll }) => {
  const [previewCode, setPreviewCode] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState<string>("");
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handlePreview = async (art: Artifact) => {
    setLoadingId(art.id);
    try {
      const res = await fetch(`${API_BASE}/api/artifacts/${art.id}/download`);
      if (res.ok) {
        const text = await res.text();
        setPreviewCode(text);
        setPreviewTitle(art.name);
      }
    } catch {
      // ignore
    } finally {
      setLoadingId(null);
    }
  };
  const getFileIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "docx":
      case "doc":
        return <FileText className="w-4 h-4 text-blue-400" />;
      case "xlsx":
      case "csv":
        return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
      case "pptx":
        return <Presentation className="w-4 h-4 text-orange-400" />;
      case "py":
        return <Code2 className="w-4 h-4 text-yellow-400" />;
      case "fcstd":
      case "stl":
      case "dxf":
        return <Box className="w-4 h-4 text-cyan-400" />;
      case "svg":
      case "png":
      case "jpg":
        return <ImageIcon className="w-4 h-4 text-purple-400" />;
      default:
        return <FileCheck className="w-4 h-4 text-slate-400" />;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: "#111", border: "1px solid #1e1e1e" }}>
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ borderBottom: "1px solid #1e1e1e", background: "#0e0e0e" }}
      >
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-[11px] font-semibold text-white/70 tracking-wide uppercase">
            Artifacts {artifacts.length > 0 && `(${artifacts.length})`}
          </span>
        </div>
        {artifacts.length > 0 && onClearAll && (
          <button
            onClick={onClearAll}
            className="text-[10px] text-red-400/60 hover:text-red-400 flex items-center gap-1 transition cursor-pointer"
            title="Clear all artifacts"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear All</span>
          </button>
        )}
      </div>

      <div className="p-3">
        {artifacts.length === 0 ? (
          <div className="py-6 text-center">
            <p className="text-[12px] text-white/25">No artifacts yet</p>
            <p className="text-[11px] text-white/15 mt-1">Generated files will appear here</p>
          </div>
        ) : (
          <div className="space-y-2">
            {artifacts.map((art) => (
              <div
                key={art.id}
                className="flex items-center justify-between p-2.5 rounded-lg transition-all"
                style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)")}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
                  >
                    {getFileIcon(art.file_type)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-[12px] font-medium text-white/80 truncate max-w-[140px]">{art.name}</p>
                    <p className="text-[10px] text-white/30 font-mono">
                      {art.file_type.toUpperCase()} · {formatBytes(art.size_bytes)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 flex-shrink-0">
                  {["html", "py", "js", "txt", "svg", "css", "stl"].includes(art.file_type.toLowerCase()) && (
                    <button
                      onClick={() => handlePreview(art)}
                      disabled={loadingId === art.id}
                      className="flex items-center space-x-1 px-2 py-1.5 rounded-md bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-xs font-medium transition cursor-pointer"
                      title="Preview code or web output"
                    >
                      {loadingId === art.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Eye className="w-3 h-3" />
                      )}
                      <span>Preview</span>
                    </button>
                  )}

                  <a
                    href={`${API_BASE}/api/artifacts/${art.id}/download`}
                    download
                    className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 text-xs font-medium transition cursor-pointer"
                  >
                    <Download className="w-3 h-3" />
                    <span>Download</span>
                  </a>

                  {onDeleteArtifact && (
                    <button
                      onClick={() => onDeleteArtifact(art.id)}
                      className="p-1.5 rounded-md bg-white/5 hover:bg-red-500/20 text-white/40 hover:text-red-400 border border-white/10 hover:border-red-500/30 text-xs transition cursor-pointer"
                      title="Delete artifact"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {previewCode && (
        <LivePreviewModal
          isOpen={true}
          onClose={() => setPreviewCode(null)}
          code={previewCode}
          title={`Artifact Preview: ${previewTitle}`}
        />
      )}
    </div>
  );
};
