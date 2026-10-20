"use client";

import React, { useEffect, useState } from "react";
import { Cpu, PowerOff, CheckCircle2, Loader2, ChevronDown } from "lucide-react";
import { stopModels, fetchModelStatus, ModelStatus } from "@/lib/api";
import { HardwareTelemetryWidget } from "./HardwareTelemetryWidget";

interface HeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  sessionTitle: string;
}

const MODEL_OPTIONS = [
  { value: "qwen3:8b",         label: "Qwen3 8B",         badge: "Reasoning" },
  { value: "qwen3.5:4b",       label: "Qwen3.5 4B",       badge: "Fast" },
  { value: "qwen3-vl:8b",      label: "Qwen3 VL 8B",      badge: "Vision" },
  { value: "qwen2.5-coder:8b", label: "Qwen2.5 Coder 8B", badge: "Code" },
];

export const Header: React.FC<HeaderProps> = ({
  selectedModel,
  onModelChange,
  sessionTitle,
}) => {
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [isStopping, setIsStopping] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const updateStatus = async () => {
      const status = await fetchModelStatus();
      if (isMounted && status) setModelStatus(status);
    };
    updateStatus();
    const interval = setInterval(updateStatus, 10000);
    return () => { isMounted = false; clearInterval(interval); };
  }, []);

  const handleStopModel = async () => {
    setIsStopping(true);
    try {
      const res = await stopModels();
      if (res.success) {
        const updated = await fetchModelStatus();
        if (updated) setModelStatus(updated);
        setFeedback(
          res.stopped_models.length > 0
            ? `Stopped: ${res.stopped_models.join(", ")} · VRAM freed`
            : "Memory freed"
        );
      } else {
        setFeedback(res.message);
      }
    } catch {
      setFeedback("Failed to stop model");
    } finally {
      setIsStopping(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const isModelActive = modelStatus?.is_active ?? false;
  const activeModel = MODEL_OPTIONS.find((m) => m.value === selectedModel);

  return (
    <header
      className="h-14 flex items-center justify-between px-5 flex-shrink-0"
      style={{ background: "#0d0d0d", borderBottom: "1px solid #1e1e1e" }}
    >
      {/* Left: Session title */}
      <div className="flex items-center gap-3 min-w-0">
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-md font-mono flex-shrink-0"
          style={{
            background: "rgba(16,185,129,0.08)",
            border: "1px solid rgba(16,185,129,0.2)",
            color: "#10b981",
          }}
        >
          CONFIDENTIAL
        </span>
        <h2 className="text-sm font-medium text-white truncate max-w-xs">
          {sessionTitle || "Industrial AI Task Session"}
        </h2>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2.5 flex-shrink-0">
        {/* Feedback pill */}
        {feedback && (
          <div
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono animate-fade-in"
            style={{
              background: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.25)",
              color: "#6ee7b7",
            }}
          >
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            {feedback}
          </div>
        )}

        {/* Hardware Telemetry Widget */}
        <HardwareTelemetryWidget />

        {/* Sovereignty badge */}
        <div
          className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-mono"
          style={{
            background: "rgba(16,185,129,0.06)",
            border: "1px solid rgba(16,185,129,0.15)",
            color: "#34d399",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-blink-dot"
            style={{ boxShadow: "0 0 5px #10b981" }}
          />
          <span className="font-semibold">AIR-GAPPED</span>
          <span className="text-white/20">·</span>
          <span className="text-white/50">0 KB Egress</span>
        </div>

        {/* Stop Model Button */}
        <button
          onClick={handleStopModel}
          disabled={isStopping}
          title={isModelActive ? "Unload model from VRAM" : "Model is idle"}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono transition-all cursor-pointer"
          style={{
            background: isModelActive ? "rgba(239,68,68,0.08)" : "rgba(255,255,255,0.04)",
            border: isModelActive ? "1px solid rgba(239,68,68,0.3)" : "1px solid rgba(255,255,255,0.08)",
            color: isModelActive ? "#f87171" : "#666",
          }}
        >
          {isStopping ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <PowerOff className="w-3.5 h-3.5" />
          )}
          <span>{isStopping ? "Stopping..." : isModelActive ? "Stop Model" : "Model Idle"}</span>
          <span
            className="w-1.5 h-1.5 rounded-full ml-0.5"
            style={{
              background: isModelActive ? "#22c55e" : "#374151",
              boxShadow: isModelActive ? "0 0 5px #22c55e" : "none",
            }}
          />
        </button>

        {/* Model Selector */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <Cpu className="w-3.5 h-3.5 text-white/40" />
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            className="bg-transparent text-[12px] text-white/80 focus:outline-none cursor-pointer font-mono"
          >
            {MODEL_OPTIONS.map((m) => (
              <option key={m.value} value={m.value} className="bg-[#1a1a1a] text-white">
                {m.label} [{m.badge}]
              </option>
            ))}
          </select>
          <ChevronDown className="w-3 h-3 text-white/30" />
        </div>
      </div>
    </header>
  );
};

