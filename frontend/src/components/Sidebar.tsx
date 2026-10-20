"use client";

import React from "react";
import {
  ShieldCheck,
  Plus,
  MessageSquare,
  Wrench,
  PencilLine,
  Search,
  Lock,
  ChevronRight,
  Cpu,
  Zap,
  Trash2,
} from "lucide-react";
import { Session, Skill } from "@/lib/api";

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession?: (id: string) => void;
  skills: Skill[];
  onSelectSkill: (skill: Skill) => void;
  activeView: "chat" | "security" | "skills";
  setActiveView: (view: "chat" | "security" | "skills") => void;
}

const skillIcons: Record<string, React.ReactNode> = {
  approval_note:     <PencilLine className="w-3.5 h-3.5" />,
  pid_analysis:      <Search className="w-3.5 h-3.5" />,
  coding:            <Cpu className="w-3.5 h-3.5" />,
  knowledge_research:<Zap className="w-3.5 h-3.5" />,
};

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  skills,
  onSelectSkill,
  activeView,
  setActiveView,
}) => {
  return (
    <aside className="w-60 bg-[#111111] border-r border-[#222] flex flex-col h-screen text-white select-none flex-shrink-0">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-[#222]">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 0 16px rgba(16,185,129,0.3)" }}
          >
            <Lock className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-[13px] font-semibold tracking-tight text-white leading-tight">MRPL Sovereign AI</h1>
            <p className="text-[10px] text-emerald-500 font-mono flex items-center gap-1 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-blink-dot inline-block" />
              AIR-GAPPED
            </p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-3">
        <button
          onClick={onNewSession}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium text-white transition-all cursor-pointer group"
          style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.09)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
        >
          <Plus className="w-4 h-4 text-white/60 group-hover:text-white transition-colors" />
          <span>New Task Session</span>
        </button>
      </div>

      {/* Nav Tabs */}
      <div className="px-3 pb-3 flex gap-1.5">
        <button
          onClick={() => setActiveView("chat")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-all cursor-pointer ${
            activeView === "chat"
              ? "bg-white/10 text-white"
              : "text-white/40 hover:text-white/70 hover:bg-white/5"
          }`}
        >
          <MessageSquare className="w-3 h-3" />
          <span>Chat</span>
        </button>
        <button
          onClick={() => setActiveView("security")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-all cursor-pointer ${
            activeView === "security"
              ? "bg-white/10 text-emerald-400"
              : "text-white/40 hover:text-white/70 hover:bg-white/5"
          }`}
        >
          <ShieldCheck className="w-3 h-3" />
          <span>Security</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-0.5 no-scrollbar">
        {sessions.length > 0 && (
          <p className="text-[10px] font-semibold text-white/25 uppercase tracking-widest px-2 pb-1.5 pt-1">
            Sessions
          </p>
        )}
        {sessions.length === 0 ? (
          <div className="px-2 py-6 text-center">
            <MessageSquare className="w-6 h-6 mx-auto text-white/15 mb-2" />
            <p className="text-[11px] text-white/30">No sessions yet</p>
          </div>
        ) : (
          sessions.map((sess) => (
            <div
              key={sess.id}
              className={`w-full group rounded-lg transition-all flex items-center justify-between pr-1.5 ${
                activeSessionId === sess.id
                  ? "bg-white/10 text-white font-medium"
                  : "text-white/50 hover:bg-white/5 hover:text-white/80"
              }`}
            >
              <button
                onClick={() => { onSelectSession(sess.id); setActiveView("chat"); }}
                className="flex-1 text-left px-2.5 py-2 text-[12px] truncate flex items-center gap-2 cursor-pointer min-w-0"
              >
                <MessageSquare className="w-3 h-3 flex-shrink-0 text-white/30 group-hover:text-white/50 transition-colors" />
                <span className="truncate">{sess.title}</span>
              </button>
              {onDeleteSession && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(sess.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-white/30 hover:text-red-400 transition cursor-pointer flex-shrink-0"
                  title="Delete chat session"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          ))
        )}

        {/* Skills Section */}
        <div className="pt-4">
          <p className="text-[10px] font-semibold text-white/25 uppercase tracking-widest px-2 pb-1.5 flex items-center justify-between">
            <span>Domain Skills</span>
            <Wrench className="w-3 h-3 text-white/20" />
          </p>
          <div className="space-y-0.5">
            {skills.map((skill) => (
              <button
                key={skill.name}
                onClick={() => onSelectSkill(skill)}
                className="w-full text-left px-2.5 py-1.5 rounded-lg text-[12px] text-white/40 hover:bg-white/5 hover:text-emerald-400 transition-all flex items-center gap-2 cursor-pointer group"
                title={skill.purpose}
              >
                <span className="text-white/20 group-hover:text-emerald-500 transition-colors flex-shrink-0">
                  {skillIcons[skill.name] || <ChevronRight className="w-3.5 h-3.5" />}
                </span>
                <span className="truncate capitalize">{skill.name.replace(/_/g, " ")}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer — Local Models */}
      <div className="px-3 pb-4 pt-3 border-t border-[#222] space-y-1.5">
        <p className="text-[10px] font-semibold text-white/25 uppercase tracking-widest px-1 pb-1 flex items-center justify-between">
          <span>Local Models</span>
          <Cpu className="w-3 h-3 text-white/20" />
        </p>
        {[
          { name: "Qwen3 8B", tag: "Reasoning" },
          { name: "Qwen3 VL 8B", tag: "Vision" },
          { name: "Qwen2.5 Coder", tag: "Code" },
        ].map((m) => (
          <div key={m.name} className="flex items-center justify-between px-2 py-1.5 rounded-md bg-white/[0.03] border border-white/5">
            <span className="text-[11px] text-white/50 font-mono">{m.name}</span>
            <span className="text-[9px] text-emerald-500 font-semibold font-mono px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              {m.tag}
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
};

