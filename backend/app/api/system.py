"""
Sovereign AI Workbench — Hardware Telemetry Endpoints
Provides real-time machine telemetry for:
- CPU: Utilization %, Cores, Frequency
- RAM: Used / Total GB, Percent
- Dedicated GPU: NVIDIA GeForce RTX 3050 (Load %, VRAM, Temp)
- Integrated GPU: Intel(R) UHD Graphics (Load %, Memory)
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.telemetry_service import telemetry_manager

router = APIRouter(prefix="/api/system", tags=["system"])


class CpuTelemetry(BaseModel):
    percent: float
    cores: int
    freq_ghz: float


class RamTelemetry(BaseModel):
    percent: float
    used_gb: float
    total_gb: float


class DgpuTelemetry(BaseModel):
    name: str
    load_percent: float
    vram_used_mb: float
    vram_total_mb: float
    temp_c: float
    status: str


class IgpuTelemetry(BaseModel):
    name: str
    load_percent: float
    dedicated_mb: float
    shared_mb: float
    status: str


class HardwareTelemetryResponse(BaseModel):
    cpu: CpuTelemetry
    ram: RamTelemetry
    dgpu: DgpuTelemetry
    igpu: IgpuTelemetry
    timestamp: float


@router.get("/telemetry", response_model=HardwareTelemetryResponse)
async def get_system_telemetry() -> HardwareTelemetryResponse:
    """Get the current real-time hardware telemetry snapshot."""
    raw = telemetry_manager.get_telemetry()
    return HardwareTelemetryResponse(**raw)
