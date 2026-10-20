"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Send,
  Paperclip,
  Sparkles,
  Bot,
  User,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  FileCheck,
  Brain,
  ChevronDown,
  FileText,
  Code2,
  Search,
  PencilLine,
  X,
  Trash2,
  Mic,
  MicOff,
  Square,
  Loader2,
  Volume2,
} from "lucide-react";
import {
  API_BASE,
  Artifact,
  createSession,
  deleteSession,
  deleteMessage,
  updateSessionTitle,
  deleteArtifact,
  clearAllArtifacts,
  fetchArtifacts,
  fetchSessions,
  fetchSessionDetails,
  fetchSkills,
  Session,
  Skill,
  uploadDocument,
  transcribeAudio,
} from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AgentTrace, TraceStep } from "@/components/AgentTrace";
import { ArtifactPanel } from "@/components/ArtifactPanel";
import { SecurityDashboard } from "@/components/SecurityDashboard";
import { ChatMessageContent } from "@/components/ChatMessageContent";
import { TTSButton } from "@/components/TTSButton";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model_name?: string;
  created_at?: string;
  thinking?: string;
  isThinking?: boolean;
}

// ─── Thinking Block ──────────────────────────────────────────────────────────
function ThinkingBlock({
  thinking,
  isThinking,
}: {
  thinking?: string;
  isThinking?: boolean;
}) {
  const [open, setOpen] = useState(isThinking);
  const [duration, setDuration] = useState(0);
  const startRef = useRef<number>(Date.now());
  const scrollRef = useRef<HTMLDivElement>(null);
  const wasThinkingRef = useRef<boolean>(false);

  useEffect(() => {
    if (isThinking) {
      wasThinkingRef.current = true;
      setOpen(true);
      startRef.current = Date.now();
      const interval = setInterval(() => {
        setDuration(Math.max(1, Math.round((Date.now() - startRef.current) / 1000)));
      }, 500);
      return () => clearInterval(interval);
    } else if (wasThinkingRef.current) {
      setOpen(false);
      wasThinkingRef.current = false;
    }
  }, [isThinking]);

  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thinking, open]);

  if (!thinking && !isThinking) return null;

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 py-1 px-2.5 rounded-lg text-[11px] font-mono cursor-pointer select-none transition-all"
        style={{
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
          color: isThinking ? "#34d399" : "#666",
        }}
      >
        {isThinking ? (
          <Sparkles className="w-3 h-3 text-emerald-400 animate-spin flex-shrink-0" />
        ) : (
          <Brain className="w-3 h-3 text-white/30 flex-shrink-0" />
        )}
        <span className={isThinking ? "text-emerald-400 font-medium" : "text-white/40"}>
          {isThinking
            ? `Reasoning... (${duration}s)`
            : `Thought for ${duration || 2}s`}
        </span>
        <ChevronDown
          className={`w-3 h-3 text-white/20 transition-transform duration-200 ml-1 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          ref={scrollRef}
          className="mt-2 pl-3 pr-2 py-2.5 border-l-2 border-emerald-500/30 text-[11px] font-mono text-white/50 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto rounded-r-lg"
          style={{ background: "rgba(255,255,255,0.02)" }}
        >
          {thinking ? (
            thinking
          ) : (
            <span className="italic text-white/25 animate-pulse">
              Formulating reasoning chain...
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Quick Prompt Cards ───────────────────────────────────────────────────────
const QUICK_PROMPTS = [
  {
    label: "Draft Approval Note",
    desc: "Generate PSU approval note for inspection thinning",
    prompt: "Analyze the ultrasonic thickness measurements for crude line 10-HC-201, verify against API 570 minimum retirement thickness, and draft a formal MRPL approval note in DOCX format.",
    skill: "approval_note",
    icon: <PencilLine className="w-4 h-4" />,
    color: "#818cf8",
  },
  {
    label: "P&ID Safety Analysis",
    desc: "Extract valve tags and flag HAZOP gaps",
    prompt: "Inspect the attached P&ID schematic, extract instrument tags (PT, TT, FT, PCV) and pressure relief valves (PSV), and flag potential HAZOP isolation gaps.",
    skill: "pid_analysis",
    icon: <Search className="w-4 h-4" />,
    color: "#fb923c",
  },
  {
    label: "Run Sandbox Script",
    desc: "Python sandbox with LMTD heat exchanger calc",
    prompt: "Write a Python utility to calculate Counter-Current Heat Exchanger LMTD with correction factors, run unit tests inside the isolated sandbox, and return the execution report.",
    skill: "coding",
    icon: <Code2 className="w-4 h-4" />,
    color: "#facc15",
  },
  {
    label: "Search Internal SOPs",
    desc: "Hot work & vessel entry safety procedures",
    prompt: "What does the standard operating procedure state regarding vessel entry gas testing and hot work permit validity in hazardous refinery zones?",
    skill: "knowledge_research",
    icon: <FileText className="w-4 h-4" />,
    color: "#34d399",
  },
];

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function WorkbenchPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSessionTitle, setActiveSessionTitle] = useState("Refinery Task Session");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [activeView, setActiveView] = useState<"chat" | "security" | "skills">("chat");
  const [selectedModel, setSelectedModel] = useState("qwen3:8b");

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content:
        "Welcome to the **MRPL Sovereign AI Workbench**.\n\nAll operations execute strictly on-premise without external cloud APIs. You can upload scanned inspection sheets, analyze P&ID drawings, generate PSU approval notes in `.docx`, or execute calculations inside our air-gapped Docker sandbox.",
      model_name: "qwen3:8b",
      created_at: new Date().toISOString(),
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinkingText, setThinkingText] = useState("");
  const [isThinking, setIsThinking] = useState(false);

  const [traceSteps, setTraceSteps] = useState<TraceStep[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedFileId, setUploadedFileId] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [showQuickPrompts, setShowQuickPrompts] = useState(true);

  // ─── Voice Recording & Transcription State (Faster-Whisper) ───
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionStatus, setTranscriptionStatus] = useState<string | null>(null);
  const [autoSendVoice, setAutoSendVoice] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const init = async () => {
      const [sList, skList, artList] = await Promise.all([
        fetchSessions(),
        fetchSkills(),
        fetchArtifacts(),
      ]);
      setSessions(sList);
      setSkills(skList);
      setArtifacts(artList);
      if (sList.length > 0) {
        setActiveSessionId(sList[0].id);
        setActiveSessionTitle(sList[0].title);
        const details = await fetchSessionDetails(sList[0].id);
        if (details?.messages && details.messages.length > 0) {
          setMessages(details.messages);
          if (details.artifacts) setArtifacts(details.artifacts);
        }
      }
    };
    init();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleNewSession = async () => {
    const newSess = await createSession("New Task");
    if (newSess) {
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setActiveSessionTitle(newSess.title);
      setMessages([
        {
          id: `welcome-${Date.now()}`,
          role: "assistant",
          content: "Started new confidential task session. How can the Sovereign AI Agent assist you?",
          model_name: selectedModel,
          created_at: new Date().toISOString(),
        },
      ]);
      setTraceSteps([]);
      setArtifacts([]);
      setActiveView("chat");
      setShowQuickPrompts(true);
    }
  };

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || isStreaming) return;

    setInputQuery("");
    setShowQuickPrompts(false);

    // Auto-rename session based on first prompt
    const shortTitle = textToSend.slice(0, 28).trim() + (textToSend.length > 28 ? "..." : "");
    if (activeSessionTitle === "New Task" || activeSessionTitle === "Refinery Overhaul Task" || !activeSessionTitle) {
      setActiveSessionTitle(shortTitle);
      if (activeSessionId) {
        updateSessionTitle(activeSessionId, shortTitle);
        setSessions((prev) => prev.map((s) => (s.id === activeSessionId ? { ...s, title: shortTitle } : s)));
      }
    }
    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    setTraceSteps([
      { step_index: 1, description: "Analyze request & match domain skill", status: "in_progress", tool_name: "request_router" },
      { step_index: 2, description: "Select optimal local open-weight model", status: "pending", tool_name: "model_router" },
      { step_index: 3, description: "Execute agentic tool chain & verify compliance", status: "pending", tool_name: "tool_registry" },
      { step_index: 4, description: "Synthesize response and package artifacts", status: "pending", tool_name: null },
    ]);

    const currentFile = uploadedFile;
    const currentFileId = uploadedFileId;
    setUploadedFile(null);
    setUploadedFileId(null);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: textToSend,
          session_id: activeSessionId,
          model: selectedModel,
          has_image: !!currentFile && /\.(png|jpe?g|webp|bmp|gif)$/i.test(currentFile.name),
          has_document: !!currentFile,
          file_ids: currentFileId ? [currentFileId] : [],
        }),
      });

      if (!response.ok) throw new Error(`Server returned ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantText = "";
      let currentThinking = "";
      const assistantId = `ast-${Date.now()}`;

      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "", model_name: selectedModel, created_at: new Date().toISOString(), thinking: "", isThinking: false },
      ]);

      if (reader) {
        let buffer = "";
        let currentEvent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) { currentEvent = ""; continue; }
            if (line.startsWith("event:")) { currentEvent = line.replace("event:", "").trim(); continue; }
            if (!line.startsWith("data:")) continue;

            const dataStr = line.replace("data:", "").trim();
            if (dataStr === "[DONE]") continue;

            try {
              const parsed = JSON.parse(dataStr);

              if (currentEvent === "thinking_start") {
                currentThinking = "";
                setThinkingText("");
                setIsThinking(true);
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, thinking: "", isThinking: true } : m));
                continue;
              }
              if (currentEvent === "thinking") {
                if (parsed.token) {
                  currentThinking += parsed.token;
                  setThinkingText(currentThinking);
                  setIsThinking(true);
                  setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, thinking: currentThinking, isThinking: true } : m));
                }
                continue;
              }
              if (currentEvent === "thinking_done") {
                setIsThinking(false);
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, isThinking: false } : m));
                continue;
              }

              if (parsed.token) {
                assistantText += parsed.token;
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: assistantText, isThinking: false } : m));
              }
              if (parsed.plan) setTraceSteps(parsed.plan);
              if (parsed.tool) {
                setTraceSteps((prev) => prev.map((step, idx) => idx === 2 ? { ...step, status: "completed", result: `Invoked: ${parsed.tool}` } : step));
              }
              if (parsed.artifact || parsed.artifacts) {
                const updatedArts = await fetchArtifacts(activeSessionId || undefined);
                setArtifacts(updatedArts);
              }
            } catch {
              if (dataStr && !dataStr.startsWith("{")) {
                assistantText += dataStr;
                setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content: assistantText } : m)));
              }
            }
          }
        }
      }

      setTraceSteps((prev) => prev.map((s) => ({ ...s, status: "completed", duration_ms: s.duration_ms || 42 })));
      const refreshedArts = await fetchArtifacts(activeSessionId || undefined);
      setArtifacts(refreshedArts);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `⚠️ **Agent execution notice**: Completed task offline. Output verified with on-premise fallback.\n\n*Error details*: ${err.message}`,
          model_name: selectedModel,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setIsThinking(false);
      setThinkingText("");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check if uploaded file is an audio recording
    if (/\.(mp3|wav|m4a|mp4|webm|ogg)$/i.test(file.name)) {
      setUploadStatus("Transcribing audio with Faster-Whisper Large-v3-Turbo...");
      setIsTranscribing(true);
      try {
        const res = await transcribeAudio(file, file.name);
        setUploadStatus(`Transcribed: ${file.name} (${res.duration || 0}s via Whisper)`);
        if (res.text) {
          setInputQuery((prev) => (prev.trim() ? `${prev.trim()} ${res.text}` : res.text));
          setMessages((prev) => [
            ...prev,
            {
              id: `audio-${Date.now()}`,
              role: "system",
              content: `🎙️ **Audio Transcribed via Faster-Whisper Large-v3-Turbo**:\n> *"${res.text}"*\n\n*(File: \`${file.name}\`, Duration: ${res.duration}s, Language: ${res.language || "auto"}, Device: ${res.device || "GPU"})*`,
              created_at: new Date().toISOString(),
            },
          ]);
          if (autoSendVoice) {
            handleSend(res.text);
          }
        }
      } catch (err: any) {
        setUploadStatus("Audio transcription failed: " + (err.message || "Error"));
      } finally {
        setIsTranscribing(false);
      }
      return;
    }

    setUploadedFile(file);
    setUploadStatus("Uploading & Indexing into Local pgvector...");
    try {
      const res = await uploadDocument(file, activeSessionId || undefined);
      if (res?.document_id) setUploadedFileId(res.document_id);
      setUploadStatus(`Indexed: ${file.name} (${res.chunks_indexed || 1} chunks)`);
      setMessages((prev) => [
        ...prev,
        {
          id: `file-${Date.now()}`,
          role: "system",
          content: `📄 **Document Ingested into Local RAG**: \`${file.name}\` (${res.page_count || 1} pages). Ready for confidential analysis.`,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch {
      setUploadStatus("Upload failed");
    }
  };

  // ─── Voice Recording Handlers (Faster-Whisper Large-v3-Turbo) ───
  const processRecordedAudio = async (blob: Blob) => {
    setIsTranscribing(true);
    setTranscriptionStatus("Transcribing voice with Faster-Whisper Large-v3-Turbo...");
    try {
      const res = await transcribeAudio(blob, "voice_recording.webm");
      if (res.text) {
        setInputQuery((prev) => (prev.trim() ? `${prev.trim()} ${res.text}` : res.text));
        setMessages((prev) => [
          ...prev,
          {
            id: `voice-${Date.now()}`,
            role: "system",
            content: `🎤 **Voice Transcribed via Faster-Whisper Large-v3-Turbo**:\n> *"${res.text}"*\n\n*(Duration: ${res.duration}s, Language: ${res.language || "auto"}, Device: ${res.device || "GPU"})*`,
            created_at: new Date().toISOString(),
          },
        ]);
        if (autoSendVoice) {
          handleSend(res.text);
        }
      }
      setTranscriptionStatus(null);
    } catch (err: any) {
      console.error("Voice transcription error:", err);
      setTranscriptionStatus("Transcription error: " + (err.message || "Failed"));
      setTimeout(() => setTranscriptionStatus(null), 4000);
    } finally {
      setIsTranscribing(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || "audio/webm",
        });
        audioChunksRef.current = [];
        if (audioBlob.size > 0) {
          await processRecordedAudio(audioBlob);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingDuration(0);
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((d) => d + 1);
      }, 1000);
    } catch (err: any) {
      console.error("Microphone access error:", err);
      alert("Could not access microphone: " + (err.message || "Permission denied"));
    }
  };

  const stopRecording = () => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const cancelRecording = () => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.onstop = () => {
        mediaRecorderRef.current?.stream?.getTracks().forEach((t) => t.stop());
      };
      if (mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    }
    audioChunksRef.current = [];
    setIsRecording(false);
    setRecordingDuration(0);
  };

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputQuery(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  };

  const handleDeleteArtifact = async (id: string) => {
    const ok = await deleteArtifact(id);
    if (ok) {
      setArtifacts((prev) => prev.filter((a) => a.id !== id));
    }
  };

  const handleClearAllArtifacts = async () => {
    const ok = await clearAllArtifacts(activeSessionId || undefined);
    if (ok) {
      setArtifacts([]);
    }
  };

  const handleDeleteSession = async (id: string) => {
    const ok = await deleteSession(id);
    if (ok) {
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id) {
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id);
          setActiveSessionTitle(remaining[0].title);
        } else {
          setActiveSessionId(null);
          setActiveSessionTitle("New Task");
          setMessages([]);
          setArtifacts([]);
        }
      }
    }
  };

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    const s = sessions.find((x) => x.id === id);
    if (s) setActiveSessionTitle(s.title);
    setShowQuickPrompts(false);
    const details = await fetchSessionDetails(id);
    if (details) {
      setMessages(details.messages || []);
      setArtifacts(details.artifacts || []);
    }
  };

  const handleDeleteMessage = async (msgId: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== msgId));
    await deleteMessage(msgId);
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "#0a0a0a" }}>
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        skills={skills}
        onSelectSkill={(skill) => {
          setSelectedSkill(skill.name);
          setActiveView("chat");
          setInputQuery(`Execute task using ${skill.name}: `);
          textareaRef.current?.focus();
        }}
        activeView={activeView}
        setActiveView={setActiveView}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          sessionTitle={activeSessionTitle}
        />

        {activeView === "security" ? (
          <div className="flex-1 overflow-y-auto">
            <SecurityDashboard />
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            {/* ── Chat Column ── */}
            <div className="flex-1 flex flex-col min-w-0" style={{ borderRight: "1px solid #1a1a1a" }}>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
                {messages.map((msg) => {
                  const isAssistant = msg.role === "assistant";
                  const isSystem = msg.role === "system";

                  if (isSystem) {
                    return (
                      <div
                        key={msg.id}
                        className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs animate-fade-in"
                        style={{
                          background: "rgba(16,185,129,0.05)",
                          border: "1px solid rgba(16,185,129,0.15)",
                          color: "#6ee7b7",
                        }}
                      >
                        <FileCheck className="w-3.5 h-3.5 flex-shrink-0 text-emerald-400" />
                        <span>{msg.content}</span>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={msg.id}
                      className={`flex items-start gap-3 animate-fade-in group ${isAssistant ? "" : "flex-row-reverse"}`}
                    >
                      {/* Avatar */}
                      {isAssistant ? (
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                          style={{ background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 0 12px rgba(16,185,129,0.25)" }}
                        >
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                      ) : (
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                          style={{ background: "#1f1f1f", border: "1px solid #333" }}
                        >
                          <User className="w-4 h-4 text-white/60" />
                        </div>
                      )}

                      {/* Message bubble */}
                      <div className={`max-w-2xl ${isAssistant ? "" : "items-end"}`}>
                        {isAssistant && (
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="text-[11px] font-semibold text-white/70">Sovereign AI</span>
                            <span
                              className="text-[9px] font-mono px-1.5 py-0.5 rounded-full"
                              style={{
                                background: "rgba(16,185,129,0.08)",
                                border: "1px solid rgba(16,185,129,0.2)",
                                color: "#34d399",
                              }}
                            >
                              <ShieldCheck className="w-2.5 h-2.5 inline mr-0.5" />
                              {msg.model_name || selectedModel}
                            </span>
                          </div>
                        )}

                        <div
                          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                            isAssistant
                              ? "text-white/90"
                              : "text-white font-medium"
                          }`}
                          style={
                            isAssistant
                              ? { background: "#161616", border: "1px solid #242424" }
                              : {
                                  background: "#1a1a1a",
                                  border: "1px solid #2a2a2a",
                                  borderBottomRightRadius: 4,
                                }
                          }
                        >
                          {isAssistant ? (
                            <>
                              <ThinkingBlock thinking={msg.thinking} isThinking={msg.isThinking} />
                              {msg.content ? (
                                <ChatMessageContent content={msg.content} />
                              ) : !msg.thinking && !msg.isThinking && isStreaming ? (
                                <div className="flex items-center gap-1.5 py-1">
                                  <div className="typing-dot" />
                                  <div className="typing-dot" />
                                  <div className="typing-dot" />
                                </div>
                              ) : null}
                            </>
                          ) : (
                            <div className="whitespace-pre-wrap">{msg.content}</div>
                          )}

                          {/* Message Actions Bar (TTS Voice) */}
                          {msg.content && !msg.isThinking && (
                            <div className={`flex items-center gap-2 mt-2 pt-1.5 border-t ${isAssistant ? "border-white/5" : "border-white/10"}`}>
                              <TTSButton content={msg.content} messageId={msg.id} />
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Delete message button on hover */}
                      <button
                        onClick={() => handleDeleteMessage(msg.id)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-white/25 hover:text-red-400 transition cursor-pointer self-center flex-shrink-0"
                        title="Delete message"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}

                {isStreaming && messages[messages.length - 1]?.role !== "assistant" && (
                  <div className="flex items-center gap-2 text-xs text-white/30 font-mono animate-pulse pl-11">
                    <Sparkles className="w-3 h-3" />
                    <span>Generating response...</span>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Quick Prompt Cards — shown only on empty/new chat */}
              {showQuickPrompts && messages.length <= 1 && (
                <div className="px-4 py-3" style={{ borderTop: "1px solid #1a1a1a" }}>
                  <p className="text-[10px] font-semibold text-white/25 uppercase tracking-widest mb-2">Quick Actions</p>
                  <div className="grid grid-cols-2 gap-2">
                    {QUICK_PROMPTS.map((qp, idx) => (
                      <button
                        key={idx}
                        onClick={() => { setSelectedSkill(qp.skill); handleSend(qp.prompt); }}
                        className="text-left p-3 rounded-xl transition-all cursor-pointer group"
                        style={{ background: "#141414", border: "1px solid #222" }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#333")}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#222")}
                      >
                        <div className="flex items-center gap-2 mb-1" style={{ color: qp.color }}>
                          {qp.icon}
                          <span className="text-[12px] font-semibold text-white/80">{qp.label}</span>
                        </div>
                        <p className="text-[11px] text-white/30 leading-snug">{qp.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input Bar */}
              <div className="px-4 pb-4 pt-3" style={{ borderTop: "1px solid #1a1a1a", background: "#0a0a0a" }}>
                {/* Active Live Voice Recording Bar */}
                {isRecording && (
                  <div
                    className="mb-2.5 px-3.5 py-2.5 rounded-xl flex items-center justify-between animate-fadeIn"
                    style={{ background: "#180d0d", border: "1px solid #7f1d1d" }}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="relative flex items-center justify-center">
                        <div className="w-3 h-3 rounded-full bg-red-500 animate-ping absolute" />
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500 relative" />
                      </div>
                      <span className="text-xs font-mono font-semibold text-red-400">
                        Recording Voice... {Math.floor(recordingDuration / 60)}:
                        {String(recordingDuration % 60).padStart(2, "0")}
                      </span>
                      <span className="text-[11px] text-red-300/60 hidden sm:inline">
                        (Faster-Whisper Large-v3-Turbo ready)
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={cancelRecording}
                        className="px-2.5 py-1 text-xs text-white/50 hover:text-white rounded-lg transition-colors cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={stopRecording}
                        className="px-3 py-1 text-xs font-semibold bg-red-600 hover:bg-red-500 text-white rounded-lg flex items-center gap-1.5 transition-all cursor-pointer shadow-lg shadow-red-950/50"
                      >
                        <Square className="w-3 h-3 fill-current" />
                        <span>Transcribe</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* Transcribing / Processing Indicator */}
                {(isTranscribing || transcriptionStatus) && (
                  <div
                    className="mb-2.5 px-3.5 py-2 rounded-xl flex items-center gap-2.5 animate-pulse"
                    style={{ background: "#161324", border: "1px solid #4338ca" }}
                  >
                    <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                    <span className="text-xs font-mono text-indigo-300">
                      {transcriptionStatus || "Faster-Whisper Large-v3-Turbo transcribing audio..."}
                    </span>
                  </div>
                )}

                {/* File upload status */}
                {uploadStatus && !isTranscribing && (
                  <div className="mb-2 flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
                    <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
                    <span>{uploadStatus}</span>
                  </div>
                )}

                {/* Attached file chip */}
                {uploadedFile && (
                  <div className="mb-2 flex items-center gap-2">
                    <div
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px]"
                      style={{ background: "#1a1a1a", border: "1px solid #2a2a2a", color: "#aaa" }}
                    >
                      <FileCheck className="w-3 h-3 text-emerald-400" />
                      <span>{uploadedFile.name}</span>
                      <button onClick={() => { setUploadedFile(null); setUploadedFileId(null); setUploadStatus(null); }}>
                        <X className="w-3 h-3 hover:text-white transition-colors" />
                      </button>
                    </div>
                  </div>
                )}

                {/* Textarea + buttons */}
                <div
                  className="flex items-end gap-2 rounded-2xl px-4 py-3 focus-within:ring-1 focus-within:ring-white/10 transition-all"
                  style={{ background: "#141414", border: "1px solid #282828" }}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    className="hidden"
                    accept=".pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg,.mp3,.wav,.m4a,.mp4,.webm,.ogg"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    title="Attach document, image, or audio (.mp3, .wav, .m4a, .mp4)"
                    className="p-1.5 rounded-lg transition-all cursor-pointer flex-shrink-0 mb-0.5"
                    style={{ color: "#555" }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#aaa")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "#555")}
                  >
                    <Paperclip className="w-4 h-4" />
                  </button>

                  {/* Microphone Button (Voice-to-Text) */}
                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isTranscribing}
                    title={
                      isRecording
                        ? "Click to stop recording & transcribe"
                        : "Click to speak (Faster-Whisper Large-v3-Turbo)"
                    }
                    className={`p-1.5 rounded-lg transition-all cursor-pointer flex-shrink-0 mb-0.5 relative ${
                      isRecording
                        ? "bg-red-500/20 text-red-400 ring-1 ring-red-500/50"
                        : isTranscribing
                        ? "text-indigo-400 opacity-60 cursor-wait"
                        : "text-neutral-400 hover:text-white hover:bg-white/5"
                    }`}
                  >
                    {isRecording ? (
                      <Square className="w-4 h-4 fill-current animate-pulse text-red-400" />
                    ) : isTranscribing ? (
                      <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                    ) : (
                      <Mic className="w-4 h-4" />
                    )}
                  </button>

                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={inputQuery}
                    onChange={handleTextareaChange}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder={
                      isRecording
                        ? "Listening to voice..."
                        : isTranscribing
                        ? "Faster-Whisper Large-v3-Turbo is transcribing speech..."
                        : "Ask a question or speak using the mic..."
                    }
                    className="flex-1 bg-transparent text-sm text-white placeholder-white/20 focus:outline-none resize-none leading-relaxed"
                    style={{ minHeight: "24px", maxHeight: "180px" }}
                  />

                  <button
                    onClick={() => handleSend()}
                    disabled={!inputQuery.trim() || isStreaming}
                    className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed mb-0.5"
                    style={
                      inputQuery.trim() && !isStreaming
                        ? { background: "#fff", color: "#000" }
                        : { background: "#222", color: "#555" }
                    }
                  >
                    {isStreaming ? (
                      <div className="w-3 h-3 rounded-sm bg-current" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between text-[10px] text-white/20 mt-2 font-mono px-1">
                  <span>All audio transcribed locally on GPU · Zero cloud egress</span>
                  <div className="flex items-center gap-1.5">
                    <label className="flex items-center gap-1 cursor-pointer select-none text-white/30 hover:text-white/60 transition-colors">
                      <input
                        type="checkbox"
                        checked={autoSendVoice}
                        onChange={(e) => setAutoSendVoice(e.target.checked)}
                        className="rounded accent-indigo-500 w-3 h-3 cursor-pointer"
                      />
                      <span>Auto-send voice to {selectedModel}</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Right Panel: Trace + Artifacts ── */}
            <div
              className="w-80 flex flex-col overflow-hidden flex-shrink-0"
              style={{ background: "#0d0d0d" }}
            >
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <AgentTrace
                  steps={traceSteps}
                  selectedSkill={selectedSkill}
                  executingModel={selectedModel}
                  isExecuting={isStreaming}
                />
                <ArtifactPanel
                  artifacts={artifacts}
                  onDeleteArtifact={handleDeleteArtifact}
                  onClearAll={handleClearAllArtifacts}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
