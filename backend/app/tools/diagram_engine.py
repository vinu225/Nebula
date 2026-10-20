"""
Sovereign AI Workbench — Industrial Diagram & Schematic Engine
Mangalore Refinery and Petrochemicals Limited (MRPL) Industrial Standard

Generates:
1. Process Flow Diagrams (PFD) & Piping loops
2. Equipment schematics (Heat exchangers, distillation columns, pump loops)
3. Telemetry trend charts & industrial flowcharts
4. Exports in crisp SVG (vector) and high-resolution PNG via Matplotlib / Pillow
100% On-Premise, Air-Gapped, Zero-Cloud.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_refinery_diagram(user_query: str, spec_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate industrial diagram deliverables (PNG and SVG).
    Supports PFD, Distillation Loop, Heat Exchanger, Pump Station, and Flowcharts.
    """
    q = user_query.lower()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#090d12")
    ax.set_facecolor("#090d12")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # Outer engineering border
    border = patches.Rectangle((1, 1), 98, 58, linewidth=1.5, edgecolor="#0ea5e9", facecolor="none", alpha=0.6)
    ax.add_patch(border)

    # Title Banner
    title_text = "MRPL REFINERY — PROCESS FLOW & TELEMETRY SCHEMATIC"
    if "heat exchanger" in q or "lmtd" in q:
        title_text = "MRPL CRUDE PRE-HEAT TRAIN — HEAT EXCHANGER LOOP"
        # Draw Heat Exchanger Schematic
        # Shell
        shell = patches.FancyBboxPatch((30, 20), 40, 20, boxstyle="round,pad=2", edgecolor="#38bdf8", facecolor="#0f172a", lw=2)
        ax.add_patch(shell)
        ax.text(50, 30, "HEAT EXCHANGER E-101\nShell: Crude Oil (140°C -> 195°C)\nTube: Heavy Gas Oil (260°C -> 180°C)", 
                color="#f8fafc", ha="center", va="center", fontsize=10, weight="bold")
        
        # Hot In / Out
        ax.annotate("HGO Inlet\n260°C", xy=(30, 35), xytext=(12, 35),
                    arrowprops=dict(arrowstyle="->", color="#ef4444", lw=2),
                    color="#ef4444", fontsize=9, ha="center", va="center", weight="bold")
        ax.annotate("HGO Outlet\n180°C", xy=(70, 25), xytext=(88, 25),
                    arrowprops=dict(arrowstyle="<-", color="#ef4444", lw=2),
                    color="#ef4444", fontsize=9, ha="center", va="center", weight="bold")
        # Cold In / Out
        ax.annotate("Cold Crude\n140°C", xy=(40, 20), xytext=(40, 8),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2),
                    color="#38bdf8", fontsize=9, ha="center", va="center", weight="bold")
        ax.annotate("Heated Crude\n195°C", xy=(60, 40), xytext=(60, 52),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2),
                    color="#38bdf8", fontsize=9, ha="center", va="center", weight="bold")

    elif "pump" in q or "flow" in q or "loop" in q:
        title_text = "MRPL CRUDE TRANSFER PUMPING SYSTEM (P-201A/B)"
        # Draw Pump station
        # Pump A
        pump_a = patches.Circle((35, 35), 7, edgecolor="#10b981", facecolor="#0f291e", lw=2)
        ax.add_patch(pump_a)
        ax.text(35, 35, "P-201A\n(RUNNING)", color="#34d399", ha="center", va="center", fontsize=9, weight="bold")
        
        # Pump B (Standby)
        pump_b = patches.Circle((35, 18), 7, edgecolor="#64748b", facecolor="#1e293b", lw=2)
        ax.add_patch(pump_b)
        ax.text(35, 18, "P-201B\n(STANDBY)", color="#94a3b8", ha="center", va="center", fontsize=9, weight="bold")

        # Suction Manifold
        ax.annotate("Suction from\nTK-101", xy=(14, 27), xytext=(5, 27),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2),
                    color="#38bdf8", fontsize=8.5, ha="center", va="center", weight="bold")
        # Header branching to Pump A and Pump B
        ax.plot([14, 20, 20, 28], [27, 27, 35, 35], color="#38bdf8", lw=2)
        ax.plot([20, 20, 28], [27, 18, 18], color="#64748b", lw=2, linestyle="--")

        # Discharge Header combining Pump A and Pump B
        ax.plot([42, 58, 58], [35, 35, 27], color="#38bdf8", lw=2.5)
        ax.plot([42, 58, 58], [18, 18, 27], color="#64748b", lw=2, linestyle="--")
        ax.plot([58, 68], [27, 27], color="#38bdf8", lw=2.5)
        
        # P&ID Standard Hourglass Control Valve (FCV-201)
        tri_left = patches.Polygon([[68, 31], [73, 27], [68, 23]], closed=True, edgecolor="#fbbf24", facecolor="#451a03", lw=1.8)
        tri_right = patches.Polygon([[78, 31], [73, 27], [78, 23]], closed=True, edgecolor="#fbbf24", facecolor="#451a03", lw=1.8)
        ax.add_patch(tri_left)
        ax.add_patch(tri_right)
        # Valve Actuator / Diaphragm
        ax.plot([73, 73], [27, 33], color="#fbbf24", lw=1.5)
        hat = patches.Arc((73, 33), 6, 4, angle=0, theta1=0, theta2=180, edgecolor="#fbbf24", lw=1.5)
        ax.add_patch(hat)
        ax.text(73, 36, "FCV-201\n82% OPEN", color="#fbbf24", ha="center", va="bottom", fontsize=8, weight="bold")
        
        # Discharge pipe extending past valve with clean arrowhead
        ax.plot([78, 89], [27, 27], color="#38bdf8", lw=2.5)
        ax.annotate("", xy=(92, 27), xytext=(88, 27),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2.5))
        ax.text(86, 31, "Discharge to\nCDU Column", color="#38bdf8", fontsize=8, ha="center", va="bottom", weight="bold")

    elif "vdu" in q or "vacuum" in q or "residue" in q or "addon" in q or "vgo" in q:
        # Addon: Integrated CDU + VDU (Atmospheric + Vacuum Distillation Unit)
        title_text = "MRPL EXPANDED UNIT — INTEGRATED CDU + VDU COMPLEX"
        vdu_boxes = [
            ("Crude Feed\nStorage", (4, 25), "#38bdf8", (11, 13)),
            ("Desalter\nD-101", (18, 25), "#818cf8", (11, 13)),
            ("CDU Column\nC-101", (32, 16), "#10b981", (12, 32)),
            ("LPG & Naphtha", (47, 40), "#facc15", (13, 8)),
            ("Kero & Diesel", (47, 28), "#38bdf8", (13, 8)),
            ("Vacuum Furnace\nF-201", (47, 12), "#ef4444", (13, 10)),
            ("VDU Column\nC-201 (VACUUM)", (64, 9), "#06b6d4", (12, 38)),
            ("LVGO Stream", (80, 38), "#f59e0b", (15, 9)),
            ("HVGO Stream", (80, 24), "#a855f7", (15, 9)),
            ("Vacuum Residue\n(Bitumen)", (80, 10), "#ec4899", (15, 9)),
        ]
        for item in vdu_boxes:
            name, pos, color = item[0], item[1], item[2]
            size = item[3]
            rect = patches.FancyBboxPatch(pos, size[0], size[1], boxstyle="round,pad=0.7", edgecolor=color, facecolor="#0f172a", lw=2)
            ax.add_patch(rect)
            ax.text(pos[0] + size[0]/2, pos[1] + size[1]/2, name, color=color, ha="center", va="center", fontsize=7.5, weight="bold")

        # Arrows
        ax.annotate("", xy=(18, 31), xytext=(15, 31), arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=1.8))
        ax.annotate("", xy=(32, 31), xytext=(29, 31), arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=1.8))
        # CDU products
        ax.annotate("", xy=(47, 44), xytext=(44, 42), arrowprops=dict(arrowstyle="->", color="#facc15", lw=1.5))
        ax.annotate("", xy=(47, 32), xytext=(44, 32), arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.5))
        # Atmospheric residue to Vacuum Furnace
        ax.annotate("Atm. Residue", xy=(47, 17), xytext=(38, 16),
                    arrowprops=dict(arrowstyle="->", color="#ef4444", lw=2),
                    color="#ef4444", fontsize=7, ha="center", va="bottom", weight="bold")
        # Vacuum Furnace to VDU
        ax.annotate("", xy=(64, 20), xytext=(60, 17), arrowprops=dict(arrowstyle="->", color="#ef4444", lw=2))
        # VDU products
        ax.annotate("", xy=(80, 42), xytext=(76, 40), arrowprops=dict(arrowstyle="->", color="#f59e0b", lw=1.5))
        ax.annotate("", xy=(80, 28), xytext=(76, 28), arrowprops=dict(arrowstyle="->", color="#a855f7", lw=1.5))
        ax.annotate("", xy=(80, 14), xytext=(76, 15), arrowprops=dict(arrowstyle="->", color="#ec4899", lw=1.5))

    else:
        # Default: Atmospheric Distillation Unit Flow Block Diagram
        title_text = "MRPL UNIT 01 — ATMOSPHERIC DISTILLATION OVERVIEW"
        # Desalter -> Furnace -> Column -> Products
        boxes = [
            ("Crude Feed\nStorage", (5, 23), "#38bdf8", (12, 14)),
            ("Desalter\nD-101", (21, 23), "#818cf8", (12, 14)),
            ("Furnace\nF-101", (37, 23), "#ef4444", (12, 14)),
            ("CDU Column\nC-101", (53, 12), "#10b981", (13, 36)),
            ("LPG & Naphtha", (74, 38), "#facc15", (19, 10)),
            ("Kerosene / ATF", (74, 25), "#38bdf8", (19, 10)),
            ("Diesel (HSD)", (74, 12), "#34d399", (19, 10)),
        ]
        for item in boxes:
            name, pos, color = item[0], item[1], item[2]
            size = item[3] if len(item) > 3 else (14, 12)
            rect = patches.FancyBboxPatch(pos, size[0], size[1], boxstyle="round,pad=0.8", edgecolor=color, facecolor="#0f172a", lw=2)
            ax.add_patch(rect)
            ax.text(pos[0] + size[0]/2, pos[1] + size[1]/2, name, color=color, ha="center", va="center", fontsize=8.5, weight="bold")

        # Connection arrows
        ax.annotate("", xy=(21, 30), xytext=(17, 30), arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=2))
        ax.annotate("", xy=(37, 30), xytext=(33, 30), arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=2))
        ax.annotate("", xy=(53, 30), xytext=(49, 30), arrowprops=dict(arrowstyle="->", color="#ef4444", lw=2))
        ax.annotate("", xy=(74, 43), xytext=(66, 40), arrowprops=dict(arrowstyle="->", color="#facc15", lw=1.8))
        ax.annotate("", xy=(74, 30), xytext=(66, 30), arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.8))
        ax.annotate("", xy=(74, 17), xytext=(66, 20), arrowprops=dict(arrowstyle="->", color="#34d399", lw=1.8))

    # Header text
    ax.text(4, 55, title_text, color="#38bdf8", fontsize=10, weight="bold")
    ax.text(96, 55, "AIR-GAPPED SOVEREIGN DIAGRAM", color="#94a3b8", fontsize=8, ha="right")
    ax.plot([4, 96], [53, 53], color="#1e293b", lw=1)

    # Save to PNG
    png_buf = io.BytesIO()
    plt.savefig(png_buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    png_bytes = png_buf.getvalue()

    # Save to SVG
    svg_buf = io.BytesIO()
    plt.savefig(svg_buf, format="svg", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    svg_bytes = svg_buf.getvalue()

    plt.close(fig)

    slug = title_text.split("—")[-1].strip().replace(" ", "_").replace("/", "_")[:30]
    return {
        "title": title_text,
        "files": {
            "png": {
                "name": f"MRPL_{slug}_{timestamp}.png",
                "type": "png",
                "data": png_bytes,
            },
            "svg": {
                "name": f"MRPL_{slug}_{timestamp}.svg",
                "type": "svg",
                "data": svg_bytes,
            },
        },
    }
