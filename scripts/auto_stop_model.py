#!/usr/bin/env python3
"""
Sovereign AI Workbench — Model Auto-Stop & Unload Utility Script

Usage:
  python scripts/auto_stop_model.py --stop
      Immediately unloads all models from GPU VRAM and system memory.

  python scripts/auto_stop_model.py --watch [--timeout 30]
      Runs continuous inactivity watchdog. If no user query/response is
      detected for 30 minutes, it automatically shuts down / unloads the models.

  python scripts/auto_stop_model.py --status
      Displays currently loaded models in memory, VRAM usage, and inactivity time.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434"
BACKEND_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_MINUTES = 30


def _http_get(url: str, timeout: int = 5) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ModelStopScript/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> dict | None:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ModelStopScript/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
    except Exception:
        return None
    return None


def get_loaded_models() -> list[dict]:
    """Query Ollama /api/ps for models currently loaded in memory."""
    res = _http_get(f"{OLLAMA_URL}/api/ps")
    if res and "models" in res:
        return res["models"]
    return []


def unload_model(model_name: str) -> bool:
    """Unload a single model from memory via Ollama API keep_alive=0."""
    res = _http_post(
        f"{OLLAMA_URL}/api/generate",
        {"model": model_name, "keep_alive": 0},
        timeout=15,
    )
    return res is not None


def stop_all_models() -> list[str]:
    """Stop all loaded models and free VRAM/RAM."""
    print("[*] Checking running models in Ollama...")

    # First attempt stop via Backend API if running
    backend_res = _http_post(f"{BACKEND_URL}/api/models/stop", {})
    if backend_res and backend_res.get("success"):
        stopped = backend_res.get("stopped_models", [])
        if stopped:
            print(f"[+] Backend stopped active models: {', '.join(stopped)}")
            return stopped

    # Direct Ollama unload
    loaded = get_loaded_models()
    stopped = []

    if loaded:
        for m in loaded:
            name = m.get("name") or m.get("model")
            if name:
                print(f"[*] Unloading '{name}' from memory (keep_alive=0)...")
                if unload_model(name):
                    stopped.append(name)
                    print(f"    [+] Successfully unloaded '{name}'")
                else:
                    print(f"    [-] Failed to unload '{name}'")
    else:
        # Fallback check for common models to guarantee complete unload
        common_candidates = [
            "qwen3:8b",
            "qwen3.5:4b",
            "qwen3-vl:8b",
            "qwen2.5-coder:8b",
            "qwen2.5-coder:latest",
        ]
        for candidate in common_candidates:
            unload_model(candidate)

    if stopped:
        print(f"\n[SUCCESS] Unloaded {len(stopped)} model(s): {', '.join(stopped)}")
        print("[SUCCESS] All GPU VRAM and RAM have been released!")
    else:
        print("\n[INFO] No models were actively loaded in memory. Memory is already completely free.")

    return stopped


def show_status() -> None:
    """Display memory and model load status."""
    print("=" * 60)
    print("  Sovereign AI Workbench — Model Memory Status")
    print("=" * 60)

    # Check backend status
    backend_data = _http_get(f"{BACKEND_URL}/api/models/status")
    if backend_data:
        inactivity_sec = backend_data.get("inactivity_seconds", 0)
        inactivity_min = round(inactivity_sec / 60, 1)
        timeout_min = round(backend_data.get("timeout_seconds", 1800) / 60)
        print(f"[*] Backend Status: Connected")
        print(f"[*] User Inactivity: {inactivity_min} min / {timeout_min} min (Auto-stops at {timeout_min}m)")
    else:
        print("[*] Backend Status: Offline (or not yet reachable)")

    # Check Ollama ps
    loaded = get_loaded_models()
    if loaded:
        print(f"\n[*] Active Models in VRAM/RAM ({len(loaded)}):")
        for m in loaded:
            name = m.get("name", "unknown")
            size_mb = round(m.get("size", 0) / (1024 * 1024), 1)
            vram_mb = round(m.get("size_vram", m.get("size", 0)) / (1024 * 1024), 1)
            print(f"    - {name}: {size_mb} MB total ({vram_mb} MB in VRAM)")
    else:
        print("\n[*] No models currently loaded in RAM/VRAM. (0 MB consumed)")
    print("=" * 60)


def run_watchdog(timeout_minutes: int) -> None:
    """Run continuous inactivity loop for 30 minutes (or custom timeout)."""
    timeout_seconds = timeout_minutes * 60
    print("=" * 65)
    print(f"  Sovereign Model Inactivity Watchdog Started")
    print(f"  Timeout: {timeout_minutes} minutes ({timeout_seconds} seconds)")
    print(f"  Action: Auto-unload models if no user activity for {timeout_minutes}m")
    print("=" * 65)
    print("[*] Press Ctrl+C to stop watchdog.\n")

    local_last_activity = time.time()
    auto_stopped = False

    while True:
        try:
            time.sleep(15)

            # Try to get inactivity from backend
            status_data = _http_get(f"{BACKEND_URL}/api/models/status")
            if status_data:
                inactivity = status_data.get("inactivity_seconds", 0)
            else:
                inactivity = time.time() - local_last_activity

            loaded = get_loaded_models()

            if loaded:
                auto_stopped = False  # Reset flag if models are active

            if inactivity >= timeout_seconds and not auto_stopped:
                if loaded:
                    print(f"\n[!] INACTIVITY LIMIT REACHED ({round(inactivity/60, 1)}m >= {timeout_minutes}m).")
                    print("[!] Automatically stopping models to release GPU/RAM...")
                    stop_all_models()
                    auto_stopped = True
                else:
                    auto_stopped = True

        except KeyboardInterrupt:
            print("\n[*] Watchdog stopped by user.")
            break
        except Exception as e:
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Stop/Unload Ollama models on demand or after 30 min inactivity")
    parser.add_argument("--stop", action="store_true", help="Immediately unload all loaded models from memory")
    parser.add_argument("--status", action="store_true", help="Check currently running models and memory")
    parser.add_argument("--watch", action="store_true", help="Run 30-min inactivity watchdog daemon")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MINUTES, help="Inactivity timeout in minutes (default 30)")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.watch:
        run_watchdog(args.timeout)
    else:
        # Default behavior: stop/unload models immediately
        stop_all_models()


if __name__ == "__main__":
    main()
