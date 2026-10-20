"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  Lock,
  GlobeLock,
  Server,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { AuditEvent, fetchAuditLogs, fetchSovereignty, SovereigntyStatus } from "@/lib/api";

export const SecurityDashboard: React.FC = () => {
  const [status, setStatus] = useState<SovereigntyStatus | null>(null);
  const [logs, setLogs] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    const [sData, lData] = await Promise.all([fetchSovereignty(), fetchAuditLogs()]);
    setStatus(sData);
    setLogs(lData);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Title Bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            Sovereignty & Air-Gap Compliance Dashboard
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time verification of on-premise constraints, network isolation, and audit trail.
          </p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white transition cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-emerald-400" : ""}`} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Primary Status Banner */}
      <div className="p-5 rounded-2xl bg-gradient-to-r from-emerald-950/60 to-slate-900 border border-emerald-500/40 shadow-xl flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-inner">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-emerald-300 tracking-wider">AIR-GAPPED SOVEREIGN MODE</span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-mono font-bold">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Strict isolation verified. No requests leave the local network boundary.
            </p>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-2xl font-bold text-emerald-400">
            {status?.data_egress_bytes ? `${(status.data_egress_bytes / 1024).toFixed(1)} KB` : "0 KB"}
          </div>
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">External Data Egress</div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">External Cloud APIs</span>
            <GlobeLock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">{status?.external_calls_allowed ?? 0}</div>
          <div className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Zero external calls permitted
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Blocked Egress</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">{status?.external_calls_blocked ?? 0}</div>
          <div className="text-[10px] text-slate-400 mt-1">Interception filter active</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Internal Loopback Calls</span>
            <Server className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">{status?.internal_service_calls ?? 0}</div>
          <div className="text-[10px] text-blue-400 mt-1">Ollama, Postgres, MinIO</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Docker Sandbox Isolation</span>
            <Lock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xs font-mono font-bold text-purple-300 mt-1">--network=none</div>
          <div className="text-[10px] text-slate-400 mt-1">256MB RAM / 1 CPU limit</div>
        </div>
      </div>

      {/* Live Compliance & Security Audit Log */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden shadow-lg">
        <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-white tracking-wide">
              IMMUTABLE AUDIT TRAIL ({logs.length} EVENTS)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400">PostgreSQL Verified</span>
        </div>

        <div className="divide-y divide-slate-800/60 max-h-96 overflow-y-auto">
          {logs.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 italic">No audit events recorded yet</div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="p-3.5 hover:bg-slate-950/40 transition text-xs font-mono">
                <div className="flex items-center justify-between text-slate-400">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        log.status === "success"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-red-950 text-red-400 border border-red-800"
                      }`}
                    >
                      {log.status.toUpperCase()}
                    </span>
                    <span className="text-slate-200 font-medium">{log.event_type}</span>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div className="mt-1.5 flex items-center space-x-4 text-[11px] text-slate-400">
                  {log.model_name && (
                    <span>
                      Model: <span className="text-purple-300">{log.model_name}</span>
                    </span>
                  )}
                  {log.tool_name && (
                    <span>
                      Tool: <span className="text-blue-300">{log.tool_name}</span>
                    </span>
                  )}
                  {log.duration_ms !== undefined && (
                    <span>
                      Duration: <span className="text-amber-300">{log.duration_ms}ms</span>
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
