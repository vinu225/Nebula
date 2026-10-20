"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface CpuTelemetry  { percent: number; cores: number; freq_ghz: number; }
interface RamTelemetry  { percent: number; used_gb: number; total_gb: number; }
interface DgpuTelemetry { name: string; load_percent: number; vram_used_mb: number; vram_total_mb: number; temp_c: number; status: string; }
interface IgpuTelemetry { name: string; load_percent: number; dedicated_mb: number; shared_mb: number; status: string; }
interface Telemetry     { cpu: CpuTelemetry; ram: RamTelemetry; dgpu: DgpuTelemetry; igpu: IgpuTelemetry; timestamp: number; }

const HISTORY_LEN = 60; // 60 samples × 2.5s = 2.5 min window

// ─── SVG Sparkline Graph ──────────────────────────────────────────────────────
const SparkGraph: React.FC<{
  history: number[];
  color: string;
  width: number;
  height: number;
}> = ({ history, color, width, height }) => {
  if (history.length < 2) return null;

  const pad = 2;
  const w = width  - pad * 2;
  const h = height - pad * 2;

  // Build SVG path points (latest value = rightmost)
  const points = history.map((v, i) => {
    const x = pad + (i / (HISTORY_LEN - 1)) * w;
    const y = pad + h - (Math.min(100, Math.max(0, v)) / 100) * h;
    return `${x},${y}`;
  });

  const linePath  = `M ${points.join(" L ")}`;
  const firstPt   = points[0].split(",");
  const lastPt    = points[points.length - 1].split(",");
  const fillPath  = `M ${firstPt[0]},${pad + h} L ${points.join(" L ")} L ${lastPt[0]},${pad + h} Z`;

  const gradId = `grad-${color.replace("#", "")}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: "block" }}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity={0.35} />
          <stop offset="100%" stopColor={color} stopOpacity={0.0}  />
        </linearGradient>
      </defs>
      {/* Subtle grid lines */}
      {[25, 50, 75].map((pct) => {
        const gy = pad + h - (pct / 100) * h;
        return (
          <line
            key={pct}
            x1={pad} y1={gy} x2={pad + w} y2={gy}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={1}
            strokeDasharray="2,3"
          />
        );
      })}
      {/* Fill area */}
      <path d={fillPath} fill={`url(#${gradId})`} />
      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 3px ${color}99)` }}
      />
      {/* Latest dot */}
      <circle
        cx={parseFloat(lastPt[0])}
        cy={parseFloat(lastPt[1])}
        r={2.5}
        fill={color}
        style={{ filter: `drop-shadow(0 0 4px ${color})` }}
      />
    </svg>
  );
};

// ─── Single graph box (Task-Manager style) ────────────────────────────────────
const GraphBox: React.FC<{
  label: string;
  sublabel: string;
  value: number;          // 0-100 %
  history: number[];
  color: string;
  unit?: string;
}> = ({ label, sublabel, value, history, color, unit = "%" }) => {
  const BOX = 120; // square size

  const getStatusColor = () => {
    if (value >= 90) return "#f87171";
    if (value >= 75) return "#fb923c";
    return color;
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        gap: 10,
        padding: "6px 8px",
        borderRadius: 10,
        background: "rgba(15,23,42,0.7)",
        border: "1px solid rgba(51,65,85,0.6)",
        transition: "border-color 0.2s",
        cursor: "default",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${color}55`)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(51,65,85,0.6)")}
    >
      {/* Graph square */}
      <div
        style={{
          width: BOX,
          height: BOX,
          borderRadius: 7,
          background: "rgba(2,6,23,0.9)",
          border: `1px solid ${color}22`,
          overflow: "hidden",
          position: "relative",
          flexShrink: 0,
        }}
      >
        <SparkGraph history={history} color={getStatusColor()} width={BOX} height={BOX} />
        {/* Current % badge — bottom-left overlay */}
        <div
          style={{
            position: "absolute",
            bottom: 5,
            left: 6,
            fontSize: 10,
            fontFamily: "monospace",
            fontWeight: 700,
            color: getStatusColor(),
            textShadow: `0 0 8px ${getStatusColor()}`,
            letterSpacing: "0.02em",
          }}
        >
          {value.toFixed(0)}{unit}
        </div>
      </div>

      {/* Text info (right side) */}
      <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
        <span
          style={{
            color: "#e2e8f0",
            fontSize: 13,
            fontWeight: 600,
            fontFamily: "'Inter', 'Segoe UI', sans-serif",
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </span>
        <span
          style={{
            color: "#64748b",
            fontSize: 10,
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            lineHeight: 1.5,
          }}
        >
          {sublabel}
        </span>
        {/* Mini live bar */}
        <div
          style={{
            marginTop: 4,
            height: 3,
            borderRadius: 9999,
            background: "rgba(255,255,255,0.07)",
            width: "100%",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${Math.min(100, value)}%`,
              background: getStatusColor(),
              borderRadius: 9999,
              boxShadow: `0 0 6px ${getStatusColor()}66`,
              transition: "width 0.6s cubic-bezier(0.34,1.56,0.64,1)",
            }}
          />
        </div>
      </div>
    </div>
  );
};

// ─── Main Widget ──────────────────────────────────────────────────────────────
export const HardwareTelemetryWidget: React.FC = () => {
  const [telemetry, setTelemetry]     = useState<Telemetry | null>(null);
  const [expanded,  setExpanded]      = useState(false);
  const [error,     setError]         = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Rolling history buffers
  const cpuHistory  = useRef<number[]>([]);
  const ramHistory  = useRef<number[]>([]);
  const dgpuHistory = useRef<number[]>([]);
  const igpuHistory = useRef<number[]>([]);

  // Force re-render to reflect history updates
  const [, forceUpdate] = useState(0);

  const appendHistory = useCallback((buf: React.MutableRefObject<number[]>, val: number) => {
    buf.current.push(val);
    if (buf.current.length > HISTORY_LEN) buf.current.shift();
  }, []);

  // Poll backend every 2.5s
  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const res  = await fetch("http://localhost:8000/api/system/telemetry");
        if (!res.ok) throw new Error("non-200");
        const data: Telemetry = await res.json();
        if (!mounted) return;
        appendHistory(cpuHistory,  data.cpu.percent);
        appendHistory(ramHistory,  data.ram.percent);
        appendHistory(dgpuHistory, data.dgpu.load_percent);
        appendHistory(igpuHistory, data.igpu.load_percent);
        setTelemetry(data);
        setError(false);
        forceUpdate((n) => n + 1);
      } catch {
        if (mounted) setError(true);
      }
    };
    poll();
    const id = setInterval(poll, 2500);
    return () => { mounted = false; clearInterval(id); };
  }, [appendHistory]);

  // Close on outside click
  useEffect(() => {
    if (!expanded) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setExpanded(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [expanded]);

  const cpu  = telemetry?.cpu.percent   ?? 0;
  const ram  = telemetry?.ram.percent   ?? 0;
  const dgpu = telemetry?.dgpu.load_percent ?? 0;
  const igpu = telemetry?.igpu.load_percent ?? 0;

  // Pill colors
  const pills = [
    { key: "CPU", val: cpu,  color: "#38bdf8" },
    { key: "RAM", val: ram,  color: "#a78bfa" },
    { key: "RTX", val: dgpu, color: "#4ade80" },
    { key: "UHD", val: igpu, color: "#fb923c" },
  ];

  const arcR = 8;
  const circumference = 2 * Math.PI * arcR;

  return (
    <div ref={panelRef} style={{ position: "relative" }}>
      {/* ── Compact header pill ── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        title="Hardware Telemetry — click to expand"
        style={{
          display:        "flex",
          alignItems:     "center",
          gap:            5,
          padding:        "4px 10px",
          background:     "rgba(10,15,30,0.85)",
          border:         `1px solid ${expanded ? "rgba(99,102,241,0.5)" : "rgba(51,65,85,0.7)"}`,
          borderRadius:   10,
          cursor:         "pointer",
          backdropFilter: "blur(14px)",
          transition:     "border-color 0.2s, background 0.2s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(15,22,40,0.95)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(10,15,30,0.85)")}
      >
        {/* Blink dot */}
        <span
          style={{
            width: 6, height: 6, borderRadius: "50%",
            background: error ? "#f87171" : "#22d3ee",
            boxShadow:  error ? "0 0 5px #f87171" : "0 0 6px #22d3ee",
            animation:  "hw-blink 1.4s ease-in-out infinite",
            flexShrink: 0,
          }}
        />

        {pills.map(({ key, val, color }) => {
          const stroke = val >= 90 ? "#f87171" : val >= 75 ? "#fb923c" : color;
          const dash   = (Math.min(100, val) / 100) * circumference;
          return (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 3 }}>
              <span style={{ color: "#475569", fontSize: 9, fontFamily: "monospace" }}>{key}</span>
              <svg width={22} height={22} viewBox="0 0 22 22" style={{ transform: "rotate(-90deg)" }}>
                <circle cx={11} cy={11} r={arcR} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={3} />
                <circle
                  cx={11} cy={11} r={arcR} fill="none"
                  stroke={stroke} strokeWidth={3}
                  strokeDasharray={`${dash} ${circumference}`}
                  strokeLinecap="round"
                  style={{
                    transition: "stroke-dasharray 0.6s cubic-bezier(0.34,1.56,0.64,1)",
                    filter: `drop-shadow(0 0 2px ${stroke}88)`,
                  }}
                />
              </svg>
              <span style={{ color: stroke, fontSize: 10, fontFamily: "monospace", fontWeight: 700, minWidth: 24 }}>
                {Math.round(val)}%
              </span>
            </div>
          );
        })}

        <svg width={11} height={11} viewBox="0 0 12 12" fill="none"
          stroke="#475569" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.25s" }}
        >
          <path d="M2 4l4 4 4-4" />
        </svg>
      </button>

      {/* ── Expanded 2×2 Graph Panel ── */}
      {expanded && (
        <div
          style={{
            position:       "absolute",
            top:            "calc(100% + 10px)",
            right:          0,
            width:          560,
            background:     "rgba(7,11,24,0.97)",
            border:         "1px solid rgba(51,65,85,0.85)",
            borderRadius:   16,
            padding:        14,
            backdropFilter: "blur(24px)",
            boxShadow:      "0 24px 70px rgba(0,0,0,0.75), 0 0 0 1px rgba(99,102,241,0.08)",
            zIndex:         9999,
            animation:      "hw-slide-in 0.22s cubic-bezier(0.34,1.56,0.64,1)",
          }}
        >
          {/* Header row */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ fontSize: 13 }}>🖥️</span>
              <span style={{ color: "#94a3b8", fontSize: 10, fontFamily: "monospace", letterSpacing: "0.08em" }}>
                LIVE HARDWARE MONITOR
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{
                width: 5, height: 5, borderRadius: "50%", flexShrink: 0,
                background: error ? "#f87171" : "#22d3ee",
                boxShadow:  error ? "0 0 5px #f87171" : "0 0 5px #22d3ee",
                animation:  "hw-blink 1.4s ease-in-out infinite",
              }} />
              <span style={{ color: error ? "#f87171" : "#22d3ee", fontSize: 9, fontFamily: "monospace" }}>
                {error ? "OFFLINE" : "LIVE · 2.5s"}
              </span>
            </div>
          </div>

          {/* 2×2 Grid */}
          <div
            style={{
              display:             "grid",
              gridTemplateColumns: "1fr 1fr",
              gap:                 10,
            }}
          >
            {/* CPU */}
            <GraphBox
              label="CPU"
              sublabel={`${cpu.toFixed(1)}%  ·  ${telemetry?.cpu.freq_ghz ?? 2.4} GHz\n${telemetry?.cpu.cores ?? 16} logical cores`}
              value={cpu}
              history={cpuHistory.current}
              color="#38bdf8"
            />

            {/* RAM / Memory */}
            <GraphBox
              label="Memory"
              sublabel={`${telemetry?.ram.used_gb.toFixed(1) ?? "—"}/${telemetry?.ram.total_gb.toFixed(1) ?? "—"} GB  (${ram.toFixed(0)}%)`}
              value={ram}
              history={ramHistory.current}
              color="#a78bfa"
            />

            {/* Dedicated GPU */}
            <GraphBox
              label="GPU · RTX 3050"
              sublabel={`${dgpu.toFixed(1)}%  ·  ${telemetry?.dgpu.temp_c ?? 40}°C\nVRAM ${((telemetry?.dgpu.vram_used_mb ?? 0) / 1024).toFixed(1)}/${((telemetry?.dgpu.vram_total_mb ?? 6144) / 1024).toFixed(1)} GB`}
              value={dgpu}
              history={dgpuHistory.current}
              color="#4ade80"
            />

            {/* Integrated GPU */}
            <GraphBox
              label="iGPU · Intel UHD"
              sublabel={`${igpu.toFixed(1)}%  engine load\nShared ${((telemetry?.igpu.shared_mb ?? 8043) / 1024).toFixed(1)} GB`}
              value={igpu}
              history={igpuHistory.current}
              color="#fb923c"
            />
          </div>

          {/* Footer */}
          <div style={{
            marginTop:    10,
            paddingTop:   8,
            borderTop:    "1px solid rgba(51,65,85,0.4)",
            display:      "flex",
            justifyContent: "space-between",
            alignItems:   "center",
          }}>
            <span style={{ color: "#1e293b", fontSize: 9, fontFamily: "monospace" }}>
              SAMAKSH_PC  ·  Windows 11  ·  Sovereign Workbench
            </span>
            <span style={{ color: "#1e293b", fontSize: 9, fontFamily: "monospace" }}>
              {HISTORY_LEN} sample window
            </span>
          </div>
        </div>
      )}

      {/* Keyframes */}
      <style>{`
        @keyframes hw-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.25; }
        }
        @keyframes hw-slide-in {
          from { opacity: 0; transform: translateY(-10px) scale(0.96); }
          to   { opacity: 1; transform: translateY(0)    scale(1);    }
        }
      `}</style>
    </div>
  );
};
