"use client";

import React from "react";
import { CheckCircle2, CircleDashed, Clock, Terminal, Wrench, AlertCircle } from "lucide-react";

export interface TraceStep {
  step_index: number;
  description: string;
  tool_name?: string | null;
  status: "pending" | "in_progress" | "completed" | "failed";
  duration_ms?: number;
  result?: string;
  error?: string;
}

interface AgentTraceProps {
  steps: TraceStep[];
  selectedSkill?: string | null;
  executingModel?: string | null;
  isExecuting?: boolean;
}

export const AgentTrace: React.FC<AgentTraceProps> = ({
  steps,
  selectedSkill,
  executingModel,
  isExecuting,
}) => {
  if (!steps || steps.length === 0) {
    return (
      <div
        className="p-6 rounded-xl text-center"
        style={{ background: "#111", border: "1px solid #1e1e1e" }}
      >
        <Terminal className="w-7 h-7 mx-auto mb-2 opacity-20 text-white" />
        <p className="text-xs font-medium text-white/30">No active execution trace</p>
        <p className="text-[11px] text-white/20 mt-1">Submit a task to view agent steps</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: "#111", border: "1px solid #1e1e1e" }}>
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ borderBottom: "1px solid #1e1e1e", background: "#0e0e0e" }}
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-[11px] font-semibold text-white/70 tracking-wide uppercase">Execution Trace</span>
        </div>
        <div className="flex items-center gap-1.5">
          {selectedSkill && (
            <span
              className="text-[9px] font-mono px-1.5 py-0.5 rounded"
              style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)", color: "#818cf8" }}
            >
              {selectedSkill.toUpperCase()}
            </span>
          )}
          {isExecuting && (
            <span
              className="text-[9px] font-mono px-1.5 py-0.5 rounded flex items-center gap-1"
              style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)", color: "#34d399" }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
              LIVE
            </span>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="p-3 space-y-2">
        {steps.map((step) => {
          const isDone = step.status === "completed";
          const isCurrent = step.status === "in_progress";
          const isFailed = step.status === "failed";

          return (
            <div
              key={step.step_index}
              className="p-3 rounded-lg transition-all"
              style={{
                background: isCurrent ? "rgba(16,185,129,0.05)" : "rgba(255,255,255,0.02)",
                border: isCurrent
                  ? "1px solid rgba(16,185,129,0.2)"
                  : isFailed
                  ? "1px solid rgba(239,68,68,0.2)"
                  : "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  ) : isCurrent ? (
                    <CircleDashed className="w-4 h-4 text-emerald-400 animate-spin flex-shrink-0" />
                  ) : isFailed ? (
                    <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  ) : (
                    <div
                      className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-mono flex-shrink-0"
                      style={{ border: "1px solid #333", color: "#555" }}
                    >
                      {step.step_index}
                    </div>
                  )}
                  <span
                    className="text-[12px] font-medium leading-snug"
                    style={{ color: isDone ? "#aaa" : isCurrent ? "#fff" : "#666" }}
                  >
                    {step.description}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {step.tool_name && (
                    <span
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded flex items-center gap-0.5"
                      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid #2a2a2a", color: "#555" }}
                    >
                      <Wrench className="w-2 h-2" />
                      {step.tool_name}
                    </span>
                  )}
                  {step.duration_ms !== undefined && (
                    <span className="text-[9px] font-mono text-white/20 flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      {step.duration_ms}ms
                    </span>
                  )}
                </div>
              </div>

              {step.result && (
                <div
                  className="mt-2 text-[10px] font-mono px-2 py-1.5 rounded leading-relaxed"
                  style={{ background: "rgba(255,255,255,0.03)", color: "#666", border: "1px solid #1e1e1e" }}
                >
                  {step.result}
                </div>
              )}
              {step.error && (
                <div
                  className="mt-2 text-[10px] font-mono px-2 py-1.5 rounded"
                  style={{ background: "rgba(239,68,68,0.05)", color: "#f87171", border: "1px solid rgba(239,68,68,0.15)" }}
                >
                  {step.error}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};


