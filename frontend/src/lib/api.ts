/**
 * Sovereign AI Workbench — Frontend API Client
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface Session {
  id: string;
  title: string;
  user_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  name: string;
  description: string;
  purpose: string;
  required_capabilities: string[];
  required_tools: string[];
  expected_outputs: string[];
}

export interface Artifact {
  id: string;
  session_id: string;
  name: string;
  file_type: string;
  size_bytes: number;
  download_url: string;
  created_at: string;
}

export interface SovereigntyStatus {
  sovereign_mode: boolean;
  airgap_enforced: boolean;
  status: string;
  external_calls_allowed: number;
  external_calls_blocked: number;
  internal_service_calls: number;
  data_egress_bytes: number;
  uptime_seconds: number;
  allowed_endpoints: string[];
}

export interface AuditEvent {
  id: string;
  event_type: string;
  status: string;
  actor: string;
  model_name?: string;
  tool_name?: string;
  duration_ms?: number;
  timestamp: string;
  details: Record<string, any>;
}

export async function fetchSessions(): Promise<Session[]> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function createSession(title: string = "New Industrial Session"): Promise<Session | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function deleteSession(sessionId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: "DELETE",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function deleteMessage(messageId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/messages/${messageId}`, {
      method: "DELETE",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export interface SessionDetails {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    model_name?: string;
    created_at?: string;
  }>;
  tasks: any[];
  artifacts: Artifact[];
}

export async function fetchSessionDetails(sessionId: string): Promise<SessionDetails | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}


export async function fetchSkills(): Promise<Skill[]> {
  try {
    const res = await fetch(`${API_BASE}/api/skills`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchArtifacts(sessionId?: string): Promise<Artifact[]> {
  try {
    const url = sessionId ? `${API_BASE}/api/artifacts?session_id=${sessionId}` : `${API_BASE}/api/artifacts`;
    const res = await fetch(url);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function deleteArtifact(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/artifacts/${id}`, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function clearAllArtifacts(sessionId?: string): Promise<boolean> {
  try {
    const url = sessionId ? `${API_BASE}/api/artifacts?session_id=${sessionId}` : `${API_BASE}/api/artifacts`;
    const res = await fetch(url, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}


export async function fetchSovereignty(): Promise<SovereigntyStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/audit/sovereignty`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchAuditLogs(): Promise<AuditEvent[]> {
  try {
    const res = await fetch(`${API_BASE}/api/audit/events`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function uploadDocument(file: File, sessionId?: string): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  if (sessionId) {
    formData.append("session_id", sessionId);
  }
  const res = await fetch(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Upload failed");
  return await res.json();
}

export interface ModelStatus {
  loaded_models: Array<{ name?: string; model?: string; size?: number; size_vram?: number }>;
  count: number;
  inactivity_seconds: number;
  timeout_seconds: number;
  is_active: boolean;
}

export async function stopModels(): Promise<{ success: boolean; stopped_models: string[]; message: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/models/stop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to stop models");
    return await res.json();
  } catch (err: any) {
    return {
      success: false,
      stopped_models: [],
      message: err?.message || "Failed to stop models",
    };
  }
}

export async function fetchModelStatus(): Promise<ModelStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/models/status`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface TranscriptionResult {
  success: boolean;
  text: string;
  language?: string;
  language_probability?: number;
  duration?: number;
  device?: string;
  model?: string;
}

export async function transcribeAudio(
  audio: Blob | File,
  filename: string = "recording.webm",
  language?: string
): Promise<TranscriptionResult> {
  const formData = new FormData();
  formData.append("file", audio, filename);
  if (language) {
    formData.append("language", language);
  }

  const res = await fetch(`${API_BASE}/api/chat/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Transcription failed with status ${res.status}`);
  }

  return await res.json();
}

export async function synthesizeSpeech(
  text: string,
  voice: string = "en_US-lessac-medium"
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/chat/tts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text, voice }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `TTS synthesis failed with status ${res.status}`);
  }

  return await res.blob();
}

export interface TTSChunk {
  index: number;
  total: number;
  text: string;
  audioBlob: Blob;
}

export async function streamSpeech(
  text: string,
  onChunk: (chunk: TTSChunk) => void,
  voice: string = "en_US-lessac-medium",
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/tts/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text, voice }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`TTS stream failed with status ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const block of lines) {
      const match = block.match(/data:\s*([\s\S]+)/);
      if (!match) continue;
      try {
        const payload = JSON.parse(match[1]);
        if (payload.audio) {
          const binaryStr = atob(payload.audio);
          const bytes = new Uint8Array(binaryStr.length);
          for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
          }
          const audioBlob = new Blob([bytes], { type: "audio/wav" });
          onChunk({
            index: payload.index,
            total: payload.total,
            text: payload.text,
            audioBlob,
          });
        }
      } catch {
        // Skip malformed chunk
      }
    }
  }
}

