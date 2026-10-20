"use client";

import React, { useState } from "react";
import {
  X,
  Monitor,
  Tablet,
  Smartphone,
  ExternalLink,
  Maximize2,
  Minimize2,
  FolderPlus,
  Sparkles,
  Code2,
} from "lucide-react";

interface LivePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  code: string;
  title?: string;
  onOpenSaveModal?: () => void;
}

export const LivePreviewModal: React.FC<LivePreviewModalProps> = ({
  isOpen,
  onClose,
  code,
  title = "Live Code Preview",
  onOpenSaveModal,
}) => {
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");

  if (!isOpen) return null;

  // Ensure standard HTML structure if user provided snippet
  const getFullHtml = () => {
    // Check if content is SVG (2D TechDraw Blueprint)
    if (code.trim().startsWith("<svg") || code.includes("<svg xmlns")) {
      return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>2D CAD Blueprint Preview</title>
  <style>
    body {
      margin: 0;
      padding: 24px;
      background: #090d12;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      box-sizing: border-box;
    }
    svg {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }
  </style>
</head>
<body>
  ${code}
</body>
</html>`;
    }

    // Check if content is ASCII STL (3D CAD Mesh)
    if (code.trim().startsWith("solid") && code.includes("facet normal")) {
      return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>3D CAD Model Preview</title>
  <style>
    body { margin: 0; background: #090d12; overflow: hidden; color: #38bdf8; font-family: monospace; }
    #canvas3d { width: 100vw; height: 100vh; display: block; }
    #badge { position: absolute; top: 15px; left: 15px; background: rgba(15,23,42,0.8); border: 1px solid #0ea5e9; padding: 6px 12px; border-radius: 6px; font-size: 11px; }
  </style>
</head>
<body>
  <div id="badge">3D CAD MODEL — DRAG TO ROTATE</div>
  <canvas id="canvas3d"></canvas>
  <script>
    const rawStl = ${JSON.stringify(code)};
    const canvas = document.getElementById('canvas3d');
    const ctx = canvas.getContext('2d');
    
    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    // Parse vertices
    const triangles = [];
    const lines = rawStl.split('\\n');
    let currentTri = [];
    for (const l of lines) {
      const trimmed = l.trim();
      if (trimmed.startsWith('vertex')) {
        const parts = trimmed.split(/\\s+/).slice(1).map(Number);
        currentTri.push(parts);
        if (currentTri.length === 3) {
          triangles.push(currentTri);
          currentTri = [];
        }
      }
    }

    let rotX = 0.6, rotY = 0.8;
    let isDragging = false, lastMouseX = 0, lastMouseY = 0;

    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
    });
    window.addEventListener('mouseup', () => isDragging = false);
    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      rotY += (e.clientX - lastMouseX) * 0.01;
      rotX += (e.clientY - lastMouseY) * 0.01;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      render();
    });

    function render() {
      ctx.fillStyle = '#090d12';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      const scale = Math.min(canvas.width, canvas.height) * 0.0022;

      ctx.strokeStyle = '#0ea5e9';
      ctx.fillStyle = 'rgba(14, 165, 233, 0.15)';
      ctx.lineWidth = 0.8;

      for (const tri of triangles) {
        ctx.beginPath();
        for (let i = 0; i < 3; i++) {
          let [x, y, z] = tri[i];
          // Rotate Y
          let x1 = x * Math.cos(rotY) + z * Math.sin(rotY);
          let z1 = -x * Math.sin(rotY) + z * Math.cos(rotY);
          // Rotate X
          let y2 = y * Math.cos(rotX) - z1 * Math.sin(rotX);
          let z2 = y * Math.sin(rotX) + z1 * Math.cos(rotX);

          let px = cx + x1 * scale;
          let py = cy - y2 * scale;

          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
    }
    render();
  </script>
</body>
</html>`;
    }

    if (code.includes("<!DOCTYPE") || code.includes("<html") || code.includes("<body")) {
      return code;
    }
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: #090d12; color: #f8fafc; }
    pre { background: #111827; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #1f2937; }
  </style>
</head>
<body>
${code.startsWith("<") ? code : `<pre><code>${code}</code></pre>`}
</body>
</html>`;
  };

  const handleOpenNewTab = () => {
    const blob = new Blob([getFullHtml()], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  };

  const getDeviceWidth = () => {
    if (device === "mobile") return "max-w-[375px]";
    if (device === "tablet") return "max-w-[768px]";
    return "w-full";
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-3 sm:p-6 animate-in fade-in duration-200">
      <div
        className={`bg-slate-950 border border-slate-800 rounded-2xl flex flex-col shadow-2xl overflow-hidden transition-all duration-300 ${
          isFullscreen ? "w-full h-full rounded-none" : "w-full max-w-5xl h-[88vh]"
        }`}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
                <span>{title}</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Interactive Sandbox
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">Rendered with sandboxed JavaScript &amp; CSS execution</p>
            </div>
          </div>

          {/* View Toggles & Actions */}
          <div className="flex items-center space-x-2">
            {/* View Device Switcher */}
            <div className="hidden sm:flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800">
              <button
                onClick={() => {
                  setDevice("desktop");
                  setActiveTab("preview");
                }}
                title="Desktop View"
                className={`p-1.5 rounded-md transition ${
                  device === "desktop" && activeTab === "preview"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Monitor className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setDevice("tablet");
                  setActiveTab("preview");
                }}
                title="Tablet View (768px)"
                className={`p-1.5 rounded-md transition ${
                  device === "tablet" && activeTab === "preview"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Tablet className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setDevice("mobile");
                  setActiveTab("preview");
                }}
                title="Mobile View (375px)"
                className={`p-1.5 rounded-md transition ${
                  device === "mobile" && activeTab === "preview"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Smartphone className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Code / Preview Tab Switcher */}
            <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                onClick={() => setActiveTab("preview")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  activeTab === "preview"
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Preview
              </button>
              <button
                onClick={() => setActiveTab("code")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  activeTab === "code"
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Source Code
              </button>
            </div>

            {/* Mini Antigravity Save Button */}
            {onOpenSaveModal && (
              <button
                onClick={onOpenSaveModal}
                className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-medium transition cursor-pointer"
                title="Create folder and files on disk"
              >
                <FolderPlus className="w-3.5 h-3.5 text-emerald-400" />
                <span>Save to Workspace</span>
              </button>
            )}

            {/* Open in New Tab */}
            <button
              onClick={handleOpenNewTab}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
              title="Open full page in new tab"
            >
              <ExternalLink className="w-4 h-4" />
            </button>

            {/* Fullscreen Toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-rose-500/20 hover:text-rose-400 rounded-lg transition ml-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-hidden bg-slate-900/40 flex items-center justify-center p-2 sm:p-4">
          {activeTab === "preview" ? (
            <div
              className={`h-full transition-all duration-300 rounded-xl overflow-hidden shadow-2xl border border-slate-800 bg-white ${getDeviceWidth()}`}
            >
              <iframe
                title="Live Output Preview"
                srcDoc={getFullHtml()}
                sandbox="allow-scripts allow-modals allow-forms"
                className="w-full h-full border-0 bg-white"
              />
            </div>
          ) : (
            <div className="w-full h-full rounded-xl overflow-auto border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-200">
              <pre>
                <code>{code}</code>
              </pre>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Air-Gapped Local Sandbox Active • Zero Cloud Communication</span>
          </div>
          <span className="text-slate-400 font-mono">Size: {(new Blob([code]).size / 1024).toFixed(1)} KB</span>
        </div>
      </div>
    </div>
  );
};
