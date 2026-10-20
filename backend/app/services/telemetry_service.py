"""
System Hardware Telemetry Service
Reads real-time genuine hardware data on Windows:
- CPU: Usage %, Cores, Frequency (via psutil)
- RAM: Used/Total GB and % (via psutil)
- Dedicated GPU (NVIDIA RTX 3050): Core load %, VRAM used/total, Temp °C (via nvidia-smi / NVML)
- Integrated GPU (Intel UHD Graphics): Utilization %, Dedicated & Shared Memory (via DXGI & GPU Engine counter)
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import subprocess
import threading
import time
from typing import Any, Dict, Optional

import psutil

from app.core.logging import get_logger

logger = get_logger(__name__)


# --- Windows DXGI Structures for GPU Adapter Discovery ---
class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class DXGI_ADAPTER_DESC1(ctypes.Structure):
    _fields_ = [
        ("Description", wintypes.WCHAR * 128),
        ("VendorId", wintypes.UINT),
        ("DeviceId", wintypes.UINT),
        ("SubSysId", wintypes.UINT),
        ("Revision", wintypes.UINT),
        ("DedicatedVideoMemory", ctypes.c_size_t),
        ("DedicatedSystemMemory", ctypes.c_size_t),
        ("SharedSystemMemory", ctypes.c_size_t),
        ("AdapterLuid", LUID),
        ("Flags", wintypes.UINT),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SystemTelemetryManager:
    """Thread-safe background telemetry collector for CPU, RAM, dGPU, and iGPU."""

    def __init__(self, refresh_interval: float = 2.0):
        self.refresh_interval = refresh_interval
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Adapter LUID and initial memory discovery
        self.intel_luid_hex: Optional[str] = None
        self.intel_name = "Intel(R) UHD Graphics"
        self.intel_dedicated_mb = 128.0
        self.intel_shared_mb = 8048.0

        self.nvidia_name = "NVIDIA GeForce RTX 3050"
        self.nvidia_dedicated_mb = 6144.0

        self._discover_adapters()

        # Cached telemetry state
        self._latest_telemetry: Dict[str, Any] = {
            "cpu": {"percent": 0.0, "cores": psutil.cpu_count(logical=True) or 8, "freq_ghz": 2.4},
            "ram": {"percent": 0.0, "used_gb": 0.0, "total_gb": 16.0},
            "dgpu": {
                "name": self.nvidia_name,
                "load_percent": 0.0,
                "vram_used_mb": 0.0,
                "vram_total_mb": self.nvidia_dedicated_mb,
                "temp_c": 40.0,
                "status": "online",
            },
            "igpu": {
                "name": self.intel_name,
                "load_percent": 0.0,
                "dedicated_mb": self.intel_dedicated_mb,
                "shared_mb": self.intel_shared_mb,
                "status": "active",
            },
            "timestamp": time.time(),
        }

        # Initialize psutil CPU baseline
        psutil.cpu_percent(interval=None)

    def _discover_adapters(self) -> None:
        """Query DXGI adapters to find Intel & NVIDIA LUIDs and VRAM allocations."""
        try:
            IID_IDXGIFactory1 = GUID(
                0x770AAE78,
                0xF26F,
                0x4DBA,
                (ctypes.c_ubyte * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87),
            )
            factory = ctypes.c_void_p()
            hr = ctypes.windll.dxgi.CreateDXGIFactory1(
                ctypes.byref(IID_IDXGIFactory1), ctypes.byref(factory)
            )
            if hr != 0 or not factory:
                return

            p_factory = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
            EnumAdapters1_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p)
            )
            EnumAdapters1 = EnumAdapters1_proto(p_factory.contents[12])

            GetDesc1_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(DXGI_ADAPTER_DESC1)
            )
            Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)

            i = 0
            while True:
                adapter = ctypes.c_void_p()
                if EnumAdapters1(factory, i, ctypes.byref(adapter)) != 0:
                    break
                p_adapter = ctypes.cast(adapter, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
                desc = DXGI_ADAPTER_DESC1()
                GetDesc1 = GetDesc1_proto(p_adapter.contents[10])
                GetDesc1(adapter, ctypes.byref(desc))

                name = str(desc.Description).strip()
                luid_part = f"{desc.AdapterLuid.LowPart:08x}"
                ded_mb = round(desc.DedicatedVideoMemory / (1024 * 1024), 1)
                sh_mb = round(desc.SharedSystemMemory / (1024 * 1024), 1)

                if "Intel" in name:
                    self.intel_name = name
                    self.intel_luid_hex = luid_part
                    self.intel_dedicated_mb = ded_mb
                    self.intel_shared_mb = sh_mb
                elif "NVIDIA" in name:
                    self.nvidia_name = name
                    self.nvidia_dedicated_mb = ded_mb

                Release_proto(p_adapter.contents[2])(adapter)
                i += 1

            Release_proto(p_factory.contents[2])(factory)
            logger.info(
                "telemetry_adapters_discovered",
                intel=self.intel_name,
                intel_luid=self.intel_luid_hex,
                nvidia=self.nvidia_name,
            )
        except Exception as e:
            logger.warning("telemetry_dxgi_discovery_failed", error=str(e))

    def _sample_nvidia_gpu(self) -> Dict[str, Any]:
        """Query NVIDIA GPU telemetry via nvidia-smi."""
        try:
            res = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 5:
                    return {
                        "name": parts[0],
                        "load_percent": float(parts[1]),
                        "vram_used_mb": float(parts[2]),
                        "vram_total_mb": float(parts[3]),
                        "temp_c": float(parts[4]),
                        "status": "online",
                    }
        except Exception:
            pass

        return {
            "name": self.nvidia_name,
            "load_percent": 0.0,
            "vram_used_mb": 0.0,
            "vram_total_mb": self.nvidia_dedicated_mb,
            "temp_c": 40.0,
            "status": "idle",
        }

    def _sample_intel_gpu(self) -> Dict[str, Any]:
        """Query Intel iGPU engine load using Windows performance counter."""
        load_pct = 0.0
        try:
            pattern = rf"\GPU Engine(*{self.intel_luid_hex}*)\Utilization Percentage" if self.intel_luid_hex else r"\GPU Engine(*engtype_3D)\Utilization Percentage"
            cmd = ["typeperf", pattern, "-sc", "1"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            lines = [line for line in p.stdout.splitlines() if line.strip()]
            if len(lines) >= 2:
                vals_str = lines[1].split(",")
                vals = []
                for v in vals_str[1:]:
                    v_clean = v.strip().replace('"', "")
                    try:
                        vals.append(float(v_clean))
                    except ValueError:
                        pass
                if vals:
                    # Intel 3D / Video engine load peak
                    load_pct = round(max(vals), 1)
        except Exception:
            pass

        return {
            "name": self.intel_name,
            "load_percent": load_pct,
            "dedicated_mb": self.intel_dedicated_mb,
            "shared_mb": self.intel_shared_mb,
            "status": "active",
        }

    def _collect_all(self) -> Dict[str, Any]:
        """Collect real-time telemetry from all 4 components."""
        # 1. CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_freq = psutil.cpu_freq()
        freq_ghz = round(cpu_freq.current / 1000, 2) if cpu_freq else 2.4

        # 2. RAM
        mem = psutil.virtual_memory()
        ram_data = {
            "percent": mem.percent,
            "used_gb": round(mem.used / (1024**3), 2),
            "total_gb": round(mem.total / (1024**3), 2),
        }

        # 3. Dedicated GPU
        dgpu = self._sample_nvidia_gpu()

        # 4. Integrated GPU
        igpu = self._sample_intel_gpu()

        return {
            "cpu": {
                "percent": round(cpu_pct, 1),
                "cores": psutil.cpu_count(logical=True) or 8,
                "freq_ghz": freq_ghz,
            },
            "ram": ram_data,
            "dgpu": dgpu,
            "igpu": igpu,
            "timestamp": time.time(),
        }

    def _worker_loop(self) -> None:
        """Background sampling loop."""
        while self._running:
            try:
                data = self._collect_all()
                with self._lock:
                    self._latest_telemetry = data
            except Exception as e:
                logger.warning("telemetry_sampling_error", error=str(e))

            time.sleep(self.refresh_interval)

    def start(self) -> None:
        """Start the background collector thread."""
        if self._running:
            return
        self._running = True
        # Do initial collection immediately
        try:
            initial_data = self._collect_all()
            with self._lock:
                self._latest_telemetry = initial_data
        except Exception:
            pass

        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="TelemetryCollector")
        self._thread.start()
        logger.info("telemetry_service_started", interval=self.refresh_interval)

    def stop(self) -> None:
        """Stop background sampling."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def get_telemetry(self) -> Dict[str, Any]:
        """Get the latest real-time hardware telemetry snapshot instantly (<1ms)."""
        with self._lock:
            return dict(self._latest_telemetry)


# Global singleton instance
telemetry_manager = SystemTelemetryManager(refresh_interval=2.0)
