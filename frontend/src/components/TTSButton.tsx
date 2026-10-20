"use client";

import React, { useState, useEffect, useRef } from "react";
import { Volume2, VolumeX, Loader2 } from "lucide-react";
import { synthesizeSpeech } from "@/lib/api";

interface TTSButtonProps {
  content: string;
  messageId: string;
  className?: string;
}

// Global active audio coordinator so only one message plays at a time
let globalCurrentAudio: HTMLAudioElement | null = null;
let globalActiveMessageId: string | null = null;
const globalListeners = new Set<(activeId: string | null) => void>();

function setActiveAudio(audio: HTMLAudioElement | null, messageId: string | null) {
  if (globalCurrentAudio && globalCurrentAudio !== audio) {
    globalCurrentAudio.pause();
    globalCurrentAudio.currentTime = 0;
  }
  globalCurrentAudio = audio;
  globalActiveMessageId = messageId;
  globalListeners.forEach((listener) => listener(messageId));
}

// In-memory cache for audio URLs to avoid re-synthesizing same message
const audioCache = new Map<string, string>();

export const TTSButton: React.FC<TTSButtonProps> = ({ content, messageId, className = "" }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stopPlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setIsPlaying(false);
    setIsLoading(false);
    setActiveAudio(null, null);
  };

  useEffect(() => {
    const handleGlobalChange = (activeId: string | null) => {
      if (activeId !== messageId) {
        setIsPlaying(false);
        setIsLoading(false);
      }
    };
    globalListeners.add(handleGlobalChange);

    return () => {
      globalListeners.delete(handleGlobalChange);
      if (globalActiveMessageId === messageId) {
        stopPlayback();
      }
    };
  }, [messageId]);

  const handleTogglePlay = async (e: React.MouseEvent) => {
    e.stopPropagation();

    // If currently playing or loading, clicking stops it immediately
    if (isPlaying || isLoading) {
      stopPlayback();
      return;
    }

    // Stop any other currently playing message
    if (globalCurrentAudio) {
      globalCurrentAudio.pause();
      globalCurrentAudio.currentTime = 0;
      setActiveAudio(null, null);
    }

    try {
      setIsLoading(true);
      setHasError(false);

      // Check cache first for instant playback
      let audioUrl = audioCache.get(messageId);

      if (!audioUrl) {
        // Limit text for fast synthesis
        const ttsText = content.slice(0, 800);
        const blob = await synthesizeSpeech(ttsText, "en_US-lessac-medium");
        audioUrl = URL.createObjectURL(blob);
        audioCache.set(messageId, audioUrl);
      }

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setIsPlaying(false);
        setIsLoading(false);
        setActiveAudio(null, null);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setIsLoading(false);
        setHasError(true);
        setActiveAudio(null, null);
        setTimeout(() => setHasError(false), 2500);
      };

      await audio.play();
      setIsPlaying(true);
      setActiveAudio(audio, messageId);
    } catch (err) {
      console.error("TTS playback error:", err);
      setIsPlaying(false);
      setHasError(true);
      setTimeout(() => setHasError(false), 2500);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleTogglePlay}
      disabled={!content.trim()}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium transition-all cursor-pointer select-none group ${
        isPlaying
          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]"
          : hasError
          ? "bg-red-500/10 text-red-400 border border-red-500/20"
          : "text-white/40 hover:text-emerald-400 hover:bg-white/5 border border-transparent hover:border-white/10"
      } ${className}`}
      title={
        isPlaying
          ? "Stop voice playback"
          : isLoading
          ? "Generating speech (Piper TTS)..."
          : hasError
          ? "Speech synthesis failed"
          : "Listen with Piper TTS"
      }
    >
      {isLoading ? (
        <>
          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
          <span className="text-[10px] text-emerald-400/80 font-mono">Generating...</span>
        </>
      ) : isPlaying ? (
        <>
          <VolumeX className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition" />
          <span className="text-[10px] flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            Speaking
          </span>
        </>
      ) : (
        <>
          <Volume2 className="w-3.5 h-3.5 transition group-hover:scale-110" />
          <span className="text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">Listen</span>
        </>
      )}
    </button>
  );
};
