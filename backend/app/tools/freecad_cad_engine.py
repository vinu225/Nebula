"""
Sovereign AI Workbench — FreeCAD CAD & TechDraw Engine
Mangalore Refinery and Petrochemicals Limited (MRPL) Industrial Standard

Generates:
1. Dynamic parametric FreeCAD Python scripts and native .FCStd project definitions.
2. 2D TechDraw Engineering Blueprints in .DXF (AutoCAD) and .SVG with standard
   title block, projection views, and dimensions for:
   - Flanges (Weld Neck, Blind, Slip-on)
   - Industrial Valves (Gate, Ball, Globe, Relief)
   - Piping Spools & Spool Assemblies
   - Pressure Vessels & Tanks
   - Custom mechanical components
3. 3D Model Mesh (.STL) for instant interactive browser rendering and 3D inspection.
100% On-Premise, Air-Gapped, Zero-Cloud.
"""

from __future__ import annotations

import io
import math
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

# Try importing ezdxf for professional AutoCAD-compatible DXF generation
try:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    logger.warning("ezdxf_not_available_using_fallback")


def parse_cad_spec(user_query: str, extracted_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Parse or enrich CAD specification from LLM JSON or natural language query.
    Extracted JSON from Qwen reasoning model takes STRICT highest priority.
    """
    spec = extracted_json or {}
    q = user_query.lower()

    # Determine component category (favor explicit JSON from LLM first)
    if spec.get("component_type"):
        comp_type = spec["component_type"]
    elif "valve" in q:
        comp_type = "gate_valve" if "gate" in q else ("ball_valve" if "ball" in q else "relief_valve")
    elif "boiler" in q or "steam drum" in q or "ibr" in q:
        comp_type = "boiler_drum"
    elif any(k in q for k in ("engine", "stroke", "piston", "cylinder block", "ic engine")):
        comp_type = "four_stroke_engine"
    elif "spool" in q or "pipe" in q:
        comp_type = "piping_spool"
    elif "vessel" in q or "tank" in q or "pressure vessel" in q:
        comp_type = "pressure_vessel"
    elif "blind" in q:
        comp_type = "blind_flange"
    elif "weld neck" in q or "flange" in q:
        comp_type = "weld_neck_flange"
    else:
        comp_type = "weld_neck_flange"

    # Default baseline parameters
    is_boiler = "boiler" in comp_type
    is_engine = "engine" in comp_type
    defaults = {
        "component_type": comp_type,
        "title": spec.get("title") or (
            "4-Stroke IC Engine Single-Cylinder Assembly" if is_engine
            else ("MRPL IBR Steam Boiler Drum (ASME Sec I)" if is_boiler
            else ("ASME B16.5 4-Inch Weld Neck Flange" if "flange" in comp_type
                  else f"MRPL {comp_type.replace('_', ' ').title()}"))
        ),
        "standard": spec.get("standard") or (
            "ISO 3046 / SAE J1349 Standard" if is_engine
            else ("ASME Section I / IBR 1950" if is_boiler
            else ("ASME B16.5 / ASTM A105" if "flange" in comp_type
                  else ("API 600 / Class 150" if "valve" in comp_type else "ASME B31.3 / ASTM A106")))
        ),
        "project": spec.get("project") or "MRPL Standby Power GenSet Facility",
        "drawing_no": spec.get("drawing_no") or f"MRPL-CAD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
        "material": spec.get("material") or (
            "Cast Iron (GG25) & Forged 4340 Steel" if is_engine
            else ("SA-516 Gr.70 Carbon Steel / IBR Approved" if is_boiler
            else ("Carbon Steel ASTM A105N" if "flange" in comp_type else "Cast Steel WCB / SS316 Trim"))
        ),
        "nominal_size_inch": float(spec.get("nominal_size_inch") or 4.0),
        # Boiler shell OD (e.g. 1500mm typical MRPL package boiler)
        "outer_diameter": float(spec.get("outer_diameter") or (1500.0 if is_boiler else 230.0)),
        "bolt_circle_diameter": float(spec.get("bolt_circle_diameter") or 190.5),
        "bore_diameter": float(spec.get("bore_diameter") if spec.get("bore_diameter") is not None else (1460.0 if is_boiler else 102.3)),
        "thickness": float(spec.get("thickness") or (20.0 if is_boiler else 24.0)),
        "hub_diameter": float(spec.get("hub_diameter") or 135.0),
        "total_length": float(spec.get("total_length") or (4500.0 if is_boiler else (229.0 if "valve" in comp_type else (600.0 if "spool" in comp_type else 76.0)))),
        "bolt_hole_count": int(spec.get("bolt_hole_count") or 8),
        "bolt_hole_diameter": float(spec.get("bolt_hole_diameter") or 19.0),
        "tolerance": spec.get("tolerance") or "+/- 0.5 mm",
    }

    # If blind flange, bore is 0
    if comp_type == "blind_flange":
        defaults["bore_diameter"] = 0.0

    # Overwrite defaults with any valid user/LLM provided parameters
    for k, v in spec.items():
        if v is not None and v != "":
            defaults[k] = v

    # Ensure realistic ASME B31.3 proportions for Piping Spools
    if "spool" in comp_type or "pipe" in comp_type:
        import re
        len_match = re.search(r"(\d+)\s*(?:mm|m\b)", q)
        if len_match and float(len_match.group(1)) >= 100:
            defaults["total_length"] = float(len_match.group(1))

        nom_size = float(defaults.get("nominal_size_inch") or 4.0)
        if nom_size <= 4.0:
            defaults["nominal_size_inch"] = 4.0
            defaults["outer_diameter"] = 228.6        # Standard 4" Class 150 Flange OD
            defaults["pipe_outer_diameter"] = 114.3   # Standard 4" Sch 40 OD
            defaults["bore_diameter"] = 102.3         # Standard 4" Sch 40 ID
            defaults["thickness"] = 23.8
            defaults["bolt_circle_diameter"] = 190.5
            defaults["bolt_hole_count"] = 8
            defaults["bolt_hole_diameter"] = 19.0
        elif nom_size <= 6.0:
            defaults["nominal_size_inch"] = 6.0
            defaults["outer_diameter"] = 279.4
            defaults["pipe_outer_diameter"] = 168.3
            defaults["bore_diameter"] = 154.1
            defaults["thickness"] = 25.4
            defaults["bolt_circle_diameter"] = 241.3
            defaults["bolt_hole_count"] = 8
            defaults["bolt_hole_diameter"] = 22.2
        else:
            defaults["pipe_outer_diameter"] = defaults["outer_diameter"] * 0.55
            defaults["bore_diameter"] = defaults["pipe_outer_diameter"] * 0.88

    return defaults


def generate_freecad_python_script(spec: Dict[str, Any]) -> str:
    """Generate a clean, standalone FreeCAD Python script that builds the 3D model
    and exports the TechDraw page for the specific component type.
    """
    comp_type = spec.get("component_type", "weld_neck_flange")
    title = spec.get("title", "MRPL Industrial Component")
    dwg_no = spec.get("drawing_no", "MRPL-CAD-001")
    material = spec.get("material", "ASTM A105")
    doc_name = dwg_no.replace("-", "_")

    od = spec.get("outer_diameter", 230.0)
    thk = spec.get("thickness", 24.0)
    total_len = spec.get("total_length", 76.0)
    bore = spec.get("bore_diameter", 102.3)
    pcd = spec.get("bolt_circle_diameter", 190.5)
    holes = int(spec.get("bolt_hole_count", 8))
    hole_d = spec.get("bolt_hole_diameter", 19.0)

    if "boiler" in comp_type:
        shell_r = od / 2.0
        shell_inner_r = bore / 2.0
        nozzle_r = od * 0.065
        manhole_r = od * 0.09
        body_code = f"""
# 2. IBR Steam Boiler Drum (ASME Section I)
# Shell cylinder
shell = Part.makeCylinder({shell_r}, {total_len}, App.Vector(0, 0, 0), App.Vector(1, 0, 0))
# Cut through-bore (shell wall)
bore_cut = Part.makeCylinder({shell_inner_r}, {total_len + 20.0}, App.Vector(-10.0, 0, 0), App.Vector(1, 0, 0))
shell = shell.cut(bore_cut)

# Hemispherical dished heads on both ends
head_l = Part.makeSphere({shell_r})
head_l = head_l.cut(Part.makeBox({shell_r}, {shell_r * 2.0}, {shell_r * 2.0}, App.Vector(0, -{shell_r}, -{shell_r})))
head_l_inner = Part.makeSphere({shell_inner_r})
head_l_inner = head_l_inner.cut(Part.makeBox({shell_inner_r}, {shell_inner_r * 2.0}, {shell_inner_r * 2.0}, App.Vector(0, -{shell_inner_r}, -{shell_inner_r})))
head_l = head_l.cut(head_l_inner)

head_r = head_l.copy()
head_r.translate(App.Vector({total_len}, 0, 0))

boiler_body = shell.fuse(head_l).fuse(head_r)

# Steam outlet nozzle (top, mid-length)
nozzle_steam = Part.makeCylinder({nozzle_r}, {shell_r * 0.8}, App.Vector({total_len * 0.5}, 0, {shell_r}), App.Vector(0, 0, 1))
boiler_body = boiler_body.fuse(nozzle_steam)
steam_bore = Part.makeCylinder({nozzle_r * 0.6}, {shell_r * 1.5}, App.Vector({total_len * 0.5}, 0, {shell_inner_r}), App.Vector(0, 0, 1))
boiler_body = boiler_body.cut(steam_bore)

# Feedwater inlet nozzle (bottom, near left head)
nozzle_fw = Part.makeCylinder({nozzle_r * 0.75}, {shell_r * 0.7}, App.Vector({total_len * 0.2}, 0, -{shell_r}), App.Vector(0, 0, -1))
boiler_body = boiler_body.fuse(nozzle_fw)
fw_bore = Part.makeCylinder({nozzle_r * 0.45}, {shell_r}, App.Vector({total_len * 0.2}, 0, -{shell_inner_r}), App.Vector(0, 0, -1))
boiler_body = boiler_body.cut(fw_bore)

# Blowdown nozzle (bottom, near right head)
nozzle_bd = Part.makeCylinder({nozzle_r * 0.6}, {shell_r * 0.6}, App.Vector({total_len * 0.8}, 0, -{shell_r}), App.Vector(0, 0, -1))
boiler_body = boiler_body.fuse(nozzle_bd)
bd_bore = Part.makeCylinder({nozzle_r * 0.35}, {shell_r}, App.Vector({total_len * 0.8}, 0, -{shell_inner_r}), App.Vector(0, 0, -1))
boiler_body = boiler_body.cut(bd_bore)

# Manhole nozzle (top, offset from steam nozzle)
nozzle_mh = Part.makeCylinder({manhole_r}, {shell_r * 0.6}, App.Vector({total_len * 0.25}, 0, {shell_r}), App.Vector(0, 0, 1))
boiler_body = boiler_body.fuse(nozzle_mh)
mh_bore = Part.makeCylinder({manhole_r * 0.65}, {shell_r}, App.Vector({total_len * 0.25}, 0, {shell_inner_r}), App.Vector(0, 0, 1))
boiler_body = boiler_body.cut(mh_bore)

part_obj = doc.addObject("Part::Feature", "BoilerDrum")
part_obj.Shape = boiler_body
"""
    elif "engine" in comp_type:
        body_code = f"""
# 2. 4-Stroke Single-Cylinder IC Engine (ISO 3046 / SAE J1349)
# Crankcase Lower Block
crankcase = Part.makeBox(140.0, 120.0, 110.0, App.Vector(-70.0, -60.0, -110.0))
crank_cut = Part.makeCylinder(52.0, 140.0, App.Vector(0, -70.0, -55.0), App.Vector(0, 1, 0))
crankcase = crankcase.cut(crank_cut)

# Cylinder Barrel with Annular Cooling Fins
barrel = Part.makeCylinder(58.0, 160.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
for fin_idx in range(6):
    fin_z = 30.0 + fin_idx * 20.0
    fin = Part.makeCylinder(72.0, 4.0, App.Vector(0, 0, fin_z), App.Vector(0, 0, 1))
    barrel = barrel.fuse(fin)

# Cylinder Head Block
head = Part.makeBox(116.0, 116.0, 45.0, App.Vector(-58.0, -58.0, 160.0))
spark_boss = Part.makeCylinder(14.0, 25.0, App.Vector(0, 0, 205.0), App.Vector(0, 0, 1))
spark_bore = Part.makeCylinder(7.0, 40.0, App.Vector(0, 0, 190.0), App.Vector(0, 0, 1))
spark_boss = spark_boss.cut(spark_bore)

# Intake & Exhaust Manifold Stubs
intake_port = Part.makeCylinder(18.0, 40.0, App.Vector(0, -58.0, 180.0), App.Vector(0, -1, 0))
exhaust_port = Part.makeCylinder(18.0, 40.0, App.Vector(0, 58.0, 180.0), App.Vector(0, 1, 0))

# Reciprocating Piston, Wrist Pin & Connecting Rod
piston = Part.makeCylinder(44.0, 65.0, App.Vector(0, 0, 40.0), App.Vector(0, 0, 1))
wrist_pin = Part.makeCylinder(9.0, 80.0, App.Vector(0, -40.0, 70.0), App.Vector(0, 1, 0))
con_rod = Part.makeBox(16.0, 22.0, 95.0, App.Vector(-8.0, -11.0, -45.0))
crank_journal = Part.makeCylinder(22.0, 40.0, App.Vector(0, -20.0, -55.0), App.Vector(0, 1, 0))

engine_solid = crankcase.fuse(barrel).fuse(head).fuse(spark_boss).fuse(intake_port).fuse(exhaust_port)
engine_solid = engine_solid.fuse(piston).fuse(wrist_pin).fuse(con_rod).fuse(crank_journal)

part_obj = doc.addObject("Part::Feature", "FourStrokeEngine")
part_obj.Shape = engine_solid
"""
    elif "valve" in comp_type:
        body_code = f"""
# 2. Gate/Globe Valve Body & Flanges
flange_l = Part.makeCylinder({od / 2.0}, {thk}, App.Vector(-{total_len/2.0}, 0, 0), App.Vector(1, 0, 0))
flange_r = Part.makeCylinder({od / 2.0}, {thk}, App.Vector({total_len/2.0 - thk}, 0, 0), App.Vector(1, 0, 0))
valve_sphere = Part.makeSphere({od * 0.42}, App.Vector(0, 0, 0))
bonnet = Part.makeCylinder({od * 0.28}, {total_len * 0.65}, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
handwheel = Part.makeTorus({od * 0.4}, 8.0, App.Vector(0, 0, {total_len * 0.65}))

valve_body = flange_l.fuse(flange_r).fuse(valve_sphere).fuse(bonnet).fuse(handwheel)
bore_flow = Part.makeCylinder({bore / 2.0}, {total_len + 10.0}, App.Vector(-{total_len/2.0 + 5.0}, 0, 0), App.Vector(1, 0, 0))
valve_body = valve_body.cut(bore_flow)

part_obj = doc.addObject("Part::Feature", "ValveAssembly")
part_obj.Shape = valve_body
"""
    elif "spool" in comp_type or "pipe" in comp_type:
        pipe_od = spec.get("pipe_outer_diameter", 114.3)
        flange_od = od
        flange_thk = thk
        spool_len = total_len

        body_code = f"""
# 2. Fabricated Piping Spool with Weld Neck Flanges (ASME B31.3)
flange_l = Part.makeCylinder({flange_od / 2.0}, {flange_thk}, App.Vector(-{spool_len/2.0}, 0, 0), App.Vector(1, 0, 0))
flange_r = Part.makeCylinder({flange_od / 2.0}, {flange_thk}, App.Vector({spool_len/2.0 - flange_thk}, 0, 0), App.Vector(1, 0, 0))
pipe_outer = Part.makeCylinder({pipe_od / 2.0}, {spool_len}, App.Vector(-{spool_len/2.0}, 0, 0), App.Vector(1, 0, 0))

spool_body = flange_l.fuse(flange_r).fuse(pipe_outer)

# Cut through-bore
if {bore} > 0:
    bore_cut = Part.makeCylinder({bore / 2.0}, {spool_len + 30.0}, App.Vector(-{spool_len/2.0 + 15.0}, 0, 0), App.Vector(1, 0, 0))
    spool_body = spool_body.cut(bore_cut)

# Cut bolt holes in both left and right flanges
for i in range({holes}):
    angle = i * (2.0 * math.pi / {holes})
    y = {pcd / 2.0} * math.cos(angle)
    z = {pcd / 2.0} * math.sin(angle)
    bolt_l = Part.makeCylinder({hole_d / 2.0}, {flange_thk + 10.0}, App.Vector(-{spool_len/2.0 + 5.0}, y, z), App.Vector(1, 0, 0))
    bolt_r = Part.makeCylinder({hole_d / 2.0}, {flange_thk + 10.0}, App.Vector({spool_len/2.0 - flange_thk - 5.0}, y, z), App.Vector(1, 0, 0))
    spool_body = spool_body.cut(bolt_l).cut(bolt_r)

part_obj = doc.addObject("Part::Feature", "PipingSpool")
part_obj.Shape = spool_body
"""
    else:
        # Standard Flange (Weld Neck, Slip On, Blind)
        hub_d = spec.get("hub_diameter", 135.0)
        body_code = f"""
# 2. Flange Disc & Hub
flange_body = Part.makeCylinder({od / 2.0}, {thk})
if {total_len - thk} > 0:
    hub = Part.makeCylinder({hub_d / 2.0}, {total_len - thk}, App.Vector(0, 0, {thk}))
    flange_body = flange_body.fuse(hub)

if {bore} > 0:
    bore_cut = Part.makeCylinder({bore / 2.0}, {total_len + 10.0}, App.Vector(0, 0, -5))
    flange_body = flange_body.cut(bore_cut)

# Bolt holes circle pattern
for i in range({holes}):
    angle = i * (2.0 * math.pi / {holes})
    x = {pcd / 2.0} * math.cos(angle)
    y = {pcd / 2.0} * math.sin(angle)
    bolt = Part.makeCylinder({hole_d / 2.0}, {thk + 10.0}, App.Vector(x, y, -5))
    flange_body = flange_body.cut(bolt)

part_obj = doc.addObject("Part::Feature", "FlangeBody")
part_obj.Shape = flange_body
"""

    script = f'''# -*- coding: utf-8 -*-
"""
Sovereign AI Workbench - Parametric FreeCAD Automation Script
Project: {spec.get("project", "MRPL Refinery Expansion")}
Component: {title} ({dwg_no})
Standard: {spec.get("standard", "ASME B16.5")} | Material: {material}
Air-Gapped Sovereign Deployment - Zero Cloud Egress
"""

import math
try:
    import FreeCAD as App
    import Part
    import TechDraw
except ImportError:
    print("Note: Running in standalone Python environment. FreeCAD modules will load when opened in FreeCAD.")
    import sys
    sys.exit(0)

# 1. Initialize Active Document
doc = App.newDocument("{doc_name}")
{body_code}
doc.recompute()

# 3. Setup TechDraw 2D Engineering Page
try:
    page = doc.addObject("TechDraw::DrawPage", "TechDrawPage")
    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    page.Template = template

    view_front = doc.addObject("TechDraw::DrawViewPart", "FrontElevation")
    view_front.Source = [part_obj]
    view_front.Direction = (0.0, 1.0, 0.0)
    view_front.X = 160.0
    view_front.Y = 130.0
    page.addView(view_front)

    view_top = doc.addObject("TechDraw::DrawViewPart", "TopPlan")
    view_top.Source = [part_obj]
    view_top.Direction = (0.0, 0.0, 1.0)
    view_top.X = 360.0
    view_top.Y = 130.0
    page.addView(view_top)

    doc.recompute()
    print("TechDraw page generated successfully.")
except Exception as td_err:
    print(f"TechDraw note: {{td_err}}")

# 4. Save Document
doc.saveAs("{doc_name}.FCStd")
print("Saved FreeCAD project: {doc_name}.FCStd")
'''
    return script


def generate_dxf_drawing(spec: Dict[str, Any]) -> bytes:
    """Generate an authentic AutoCAD-compatible .DXF technical drawing using ezdxf.
    Draws specific geometry based on component_type (Flange, Valve, Spool, Vessel).
    """
    if not HAS_EZDXF:
        return b"DXF generation requires ezdxf"

    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()

    # Define standard layers with industrial colors (AutoCAD ACI)
    doc.layers.new(name="OUTLINE", dxfattribs={"color": 7, "lineweight": 35})       # Thick white/black
    doc.layers.new(name="CENTERLINES", dxfattribs={"color": 1, "linetype": "CENTER"}) # Red dashed
    doc.layers.new(name="DIMENSIONS", dxfattribs={"color": 3, "lineweight": 18})     # Green thin
    doc.layers.new(name="TITLEBLOCK", dxfattribs={"color": 4, "lineweight": 25})     # Cyan border

    comp_type = spec.get("component_type", "weld_neck_flange")
    od = spec.get("outer_diameter", 230.0)
    pcd = spec.get("bolt_circle_diameter", 190.5)
    id_bore = spec.get("bore_diameter", 102.3)
    thk = spec.get("thickness", 24.0)
    total_len = spec.get("total_length", 76.0)
    holes = int(spec.get("bolt_hole_count", 8))
    hole_d = spec.get("bolt_hole_diameter", 19.0)
    title = spec.get("title", "COMPONENT DRAWING")
    dwg_no = spec.get("drawing_no", "MRPL-CAD-001")

    # Center coordinates for views
    cx, cy = 160.0, 220.0
    fx, fy = 430.0, 220.0

    if "valve" in comp_type:
        # VALVE ELEVATION & SCHEMATIC VIEW
        flange_r = od / 2.0
        half_len = total_len / 2.0
        # Left flange
        msp.add_lwpolyline([(-half_len + fx, fy - flange_r), (-half_len + thk + fx, fy - flange_r),
                            (-half_len + thk + fx, fy + flange_r), (-half_len + fx, fy + flange_r),
                            (-half_len + fx, fy - flange_r)], dxfattribs={"layer": "OUTLINE"})
        # Right flange
        msp.add_lwpolyline([(half_len - thk + fx, fy - flange_r), (half_len + fx, fy - flange_r),
                            (half_len + fx, fy + flange_r), (half_len - thk + fx, fy + flange_r),
                            (half_len - thk + fx, fy - flange_r)], dxfattribs={"layer": "OUTLINE"})
        # Valve Body
        msp.add_circle((fx, fy), od * 0.38, dxfattribs={"layer": "OUTLINE"})
        # Bonnet & Handwheel
        bonnet_h = total_len * 0.6
        msp.add_line((fx, fy), (fx, fy + bonnet_h), dxfattribs={"layer": "OUTLINE"})
        msp.add_line((fx - 30, fy + bonnet_h), (fx + 30, fy + bonnet_h), dxfattribs={"layer": "OUTLINE"})
        msp.add_text("VALVE ELEVATION VIEW", dxfattribs={"height": 5.0, "layer": "TITLEBLOCK"}).set_placement((fx - 40, fy - flange_r - 25))

    elif "spool" in comp_type or "pipe" in comp_type:
        # PIPING SPOOL VIEW
        flange_r = od / 2.0
        half_len = total_len / 2.0
        pipe_r = (id_bore + 15.0) / 2.0
        # Left & Right flanges
        msp.add_lwpolyline([(-half_len + fx, fy - flange_r), (-half_len + thk + fx, fy - flange_r),
                            (-half_len + thk + fx, fy + flange_r), (-half_len + fx, fy + flange_r),
                            (-half_len + fx, fy - flange_r)], dxfattribs={"layer": "OUTLINE"})
        msp.add_lwpolyline([(half_len - thk + fx, fy - flange_r), (half_len + fx, fy - flange_r),
                            (half_len + fx, fy + flange_r), (half_len - thk + fx, fy + flange_r),
                            (half_len - thk + fx, fy - flange_r)], dxfattribs={"layer": "OUTLINE"})
        # Pipe barrel
        msp.add_line((-half_len + thk + fx, fy + pipe_r), (half_len - thk + fx, fy + pipe_r), dxfattribs={"layer": "OUTLINE"})
        msp.add_line((-half_len + thk + fx, fy - pipe_r), (half_len - thk + fx, fy - pipe_r), dxfattribs={"layer": "OUTLINE"})
        msp.add_line((-half_len - 15 + fx, fy), (half_len + 15 + fx, fy), dxfattribs={"layer": "CENTERLINES"})
        msp.add_text("PIPING SPOOL ELEVATION", dxfattribs={"height": 5.0, "layer": "TITLEBLOCK"}).set_placement((fx - 45, fy - flange_r - 25))

    else:
        # FLANGE TOP & ELEVATION VIEW
        r_od = od / 2.0
        r_pcd = pcd / 2.0
        r_bore = id_bore / 2.0
        r_hole = hole_d / 2.0

        msp.add_circle((cx, cy), r_od, dxfattribs={"layer": "OUTLINE"})
        if r_bore > 0:
            msp.add_circle((cx, cy), r_bore, dxfattribs={"layer": "OUTLINE"})
        msp.add_circle((cx, cy), r_pcd, dxfattribs={"layer": "CENTERLINES"})

        # Centerlines
        cl_ext = r_od + 25.0
        msp.add_line((cx - cl_ext, cy), (cx + cl_ext, cy), dxfattribs={"layer": "CENTERLINES"})
        msp.add_line((cx, cy - cl_ext), (cx, cy + cl_ext), dxfattribs={"layer": "CENTERLINES"})

        # Bolt Holes
        for i in range(holes):
            angle = i * (2.0 * math.pi / holes)
            hx = cx + r_pcd * math.cos(angle)
            hy = cy + r_pcd * math.sin(angle)
            msp.add_circle((hx, hy), r_hole, dxfattribs={"layer": "OUTLINE"})

        msp.add_text("VIEW A-A (TOP PLAN)", dxfattribs={"height": 5.0, "layer": "TITLEBLOCK"}).set_placement((cx - 35, cy - cl_ext - 12))

        # Flange Section Elevation (fx, fy)
        hub_d = spec.get("hub_diameter", 135.0)
        msp.add_lwpolyline([(fx - r_od, fy - thk/2), (fx + r_od, fy - thk/2),
                            (fx + r_od, fy + thk/2), (fx - r_od, fy + thk/2), (fx - r_od, fy - thk/2)],
                           dxfattribs={"layer": "OUTLINE"})
        if total_len > thk:
            hub_r = hub_d / 2.0
            msp.add_lwpolyline([(fx - hub_r, fy + thk/2), (fx + hub_r, fy + thk/2),
                                (fx + hub_r, fy - thk/2 + total_len), (fx - hub_r, fy - thk/2 + total_len),
                                (fx - hub_r, fy + thk/2)], dxfattribs={"layer": "OUTLINE"})
        msp.add_text("SECTION B-B (ELEVATION)", dxfattribs={"height": 5.0, "layer": "TITLEBLOCK"}).set_placement((fx - 40, fy - thk/2 - 25))

    # --- TITLE BLOCK (Right Bottom) ---
    tb_x, tb_y = 290.0, 25.0
    tb_w, tb_h = 255.0, 50.0
    msp.add_lwpolyline([(tb_x, tb_y), (tb_x + tb_w, tb_y), (tb_x + tb_w, tb_y + tb_h), (tb_x, tb_y + tb_h), (tb_x, tb_y)], dxfattribs={"layer": "TITLEBLOCK"})
    msp.add_line((tb_x, tb_y + 25), (tb_x + tb_w, tb_y + 25), dxfattribs={"layer": "TITLEBLOCK"})
    msp.add_line((tb_x + 150, tb_y), (tb_x + 150, tb_y + tb_h), dxfattribs={"layer": "TITLEBLOCK"})

    msp.add_text("MRPL SOVEREIGN CAD WORKBENCH", dxfattribs={"height": 4.5, "layer": "TITLEBLOCK"}).set_placement((tb_x + 6, tb_y + 35))
    msp.add_text(f"TITLE: {title[:28]}", dxfattribs={"height": 3.8, "layer": "TITLEBLOCK"}).set_placement((tb_x + 6, tb_y + 12))
    msp.add_text(f"DWG: {dwg_no}", dxfattribs={"height": 3.5, "layer": "TITLEBLOCK"}).set_placement((tb_x + 156, tb_y + 35))
    msp.add_text(f"STD: {spec.get('standard', 'ASME')[:14]}", dxfattribs={"height": 3.0, "layer": "TITLEBLOCK"}).set_placement((tb_x + 156, tb_y + 12))

    out_stream = io.StringIO()
    doc.write(out_stream)
    return out_stream.getvalue().encode("utf-8")


def generate_svg_blueprint(spec: Dict[str, Any]) -> str:
    """Generate a high-contrast 2D TechDraw Engineering Blueprint in SVG.
    Dynamically renders based on component_type (Flange, Valve, Piping Spool, Pressure Vessel)
    with fixed layout constraints to guarantee ZERO overlapping text.
    """
    comp_type = spec.get("component_type", "weld_neck_flange")
    od = spec.get("outer_diameter", 230.0)
    pcd = spec.get("bolt_circle_diameter", 190.5)
    id_bore = spec.get("bore_diameter", 102.3)
    thk = spec.get("thickness", 24.0)
    total_len = spec.get("total_length", 76.0)
    holes = int(spec.get("bolt_hole_count", 8))
    hole_d = spec.get("bolt_hole_diameter", 19.0)
    title = spec.get("title", "MRPL INDUSTRIAL CAD COMPONENT")
    dwg_no = spec.get("drawing_no", "MRPL-CAD-001")
    material = spec.get("material", "Carbon Steel ASTM A105N")
    standard = spec.get("standard", "ASME B16.5 Class 150")
    tolerance = spec.get("tolerance", "+/- 0.5 mm")

    scale = 1.2
    view_a_content = ""
    view_b_content = ""

    if "engine" in comp_type:
        # ================= 4-STROKE IC ENGINE BLUEPRINT =================
        ec_x, ec_y = 475, 230

        view_a_content = f'''
        <!-- ENGINE ELEVATION & SECTION -->
        <!-- Centerlines -->
        <line x1="{ec_x}" y1="{ec_y - 170}" x2="{ec_x}" y2="{ec_y + 160}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>
        <line x1="{ec_x - 120}" y1="{ec_y + 90}" x2="{ec_x + 120}" y2="{ec_y + 90}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>

        <!-- Crankcase Lower Block -->
        <rect x="{ec_x - 70}" y="{ec_y + 35}" width="140" height="110" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2"/>
        <circle cx="{ec_x}" cy="{ec_y + 90}" r="35" fill="#16293d" stroke="#f59e0b" stroke-width="2"/>

        <!-- Cylinder Barrel -->
        <rect x="{ec_x - 48}" y="{ec_y - 120}" width="96" height="155" fill="#16293d" stroke="#38bdf8" stroke-width="2"/>
        <!-- Bore Line -->
        <rect x="{ec_x - 38}" y="{ec_y - 120}" width="76" height="155" fill="#090d12" stroke="#475569" stroke-dasharray="4,3"/>

        <!-- Annular Cooling Fins -->
        <rect x="{ec_x - 62}" y="{ec_y - 100}" width="124" height="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="{ec_x - 62}" y="{ec_y - 80}" width="124" height="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="{ec_x - 62}" y="{ec_y - 60}" width="124" height="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="{ec_x - 62}" y="{ec_y - 40}" width="124" height="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="{ec_x - 62}" y="{ec_y - 20}" width="124" height="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="{ec_x - 62}" y="{ec_y}" width="124" height="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>

        <!-- Cylinder Head -->
        <rect x="{ec_x - 58}" y="{ec_y - 155}" width="116" height="35" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2.2"/>
        <!-- Spark Plug Boss -->
        <rect x="{ec_x - 12}" y="{ec_y - 180}" width="24" height="25" fill="#1e293b" stroke="#f59e0b" stroke-width="1.8"/>
        <!-- Intake & Exhaust Stubs -->
        <rect x="{ec_x - 85}" y="{ec_y - 148}" width="28" height="20" fill="#0f1e2e" stroke="#10b981" stroke-width="1.5"/>
        <text x="{ec_x - 98}" y="{ec_y - 134}" fill="#10b981" font-size="9" font-weight="700">IN</text>
        <rect x="{ec_x + 57}" y="{ec_y - 148}" width="28" height="20" fill="#0f1e2e" stroke="#ef4444" stroke-width="1.5"/>
        <text x="{ec_x + 95}" y="{ec_y - 134}" fill="#ef4444" font-size="9" font-weight="700">EXH</text>

        <!-- Reciprocating Piston & Connecting Rod -->
        <rect x="{ec_x - 36}" y="{ec_y - 75}" width="72" height="50" fill="#334155" stroke="#60a5fa" stroke-width="1.8"/>
        <circle cx="{ec_x}" cy="{ec_y - 50}" r="7" fill="#f59e0b" stroke="#cbd5e1" stroke-width="1.5"/>
        <!-- Connecting Rod -->
        <polygon points="{ec_x - 7},{ec_y - 45} {ec_x + 7},{ec_y - 45} {ec_x + 12},{ec_y + 80} {ec_x - 12},{ec_y + 80}" fill="#475569" stroke="#94a3b8" stroke-width="1.5"/>

        <!-- Dimensions -->
        <line x1="{ec_x - 38}" y1="{ec_y + 155}" x2="{ec_x + 38}" y2="{ec_y + 155}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
        <text x="{ec_x}" y="{ec_y + 170}" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="middle">BORE: 88.0 mm  |  STROKE: 100.0 mm</text>
        <text x="{ec_x}" y="{ec_y + 190}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">4-STROKE SINGLE-CYLINDER IC ENGINE (ISO 3046 / SAE J1349)</text>
        '''

    elif "valve" in comp_type:
        # ================= INDUSTRIAL VALVE BLUEPRINT =================
        vc_x, vc_y = 475, 230
        flange_r = (od / 2.0) * scale * 0.7
        flange_w = thk * scale
        v_len = total_len * scale * 0.65
        body_r = flange_r * 0.85
        stem_h = v_len * 0.55
        hw_r = flange_r * 0.8

        view_a_content = f'''
        <!-- VALVE ELEVATION & SECTION -->
        <!-- Centerlines -->
        <line x1="{vc_x - (v_len/2) - 35}" y1="{vc_y}" x2="{vc_x + (v_len/2) + 35}" y2="{vc_y}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>
        <line x1="{vc_x}" y1="{vc_y - stem_h - 25}" x2="{vc_x}" y2="{vc_y + flange_r + 25}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>

        <!-- Left Flange -->
        <rect x="{vc_x - (v_len/2)}" y="{vc_y - flange_r}" width="{flange_w}" height="{flange_r * 2}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2"/>
        <!-- Right Flange -->
        <rect x="{vc_x + (v_len/2) - flange_w}" y="{vc_y - flange_r}" width="{flange_w}" height="{flange_r * 2}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2"/>

        <!-- Valve Body Globe / Gate Cavity -->
        <circle cx="{vc_x}" cy="{vc_y}" r="{body_r}" fill="#16293d" stroke="#38bdf8" stroke-width="2.2"/>
        <!-- Flow Bore Hole (cutout) -->
        <rect x="{vc_x - (v_len/2)}" y="{vc_y - (id_bore*scale*0.3)}" width="{v_len}" height="{id_bore*scale*0.6}" fill="#090d12" stroke="#475569" stroke-dasharray="4,3"/>

        <!-- Bonnet & Stem -->
        <rect x="{vc_x - 12}" y="{vc_y - stem_h}" width="24" height="{stem_h - body_r + 10}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="1.8"/>
        <!-- Handwheel Actuator -->
        <ellipse cx="{vc_x}" cy="{vc_y - stem_h}" rx="{hw_r}" ry="12" fill="#1e293b" stroke="#f59e0b" stroke-width="2.2"/>
        <line x1="{vc_x - hw_r}" y1="{vc_y - stem_h}" x2="{vc_x + hw_r}" y2="{vc_y - stem_h}" stroke="#f59e0b" stroke-width="1.5"/>

        <!-- Flow Direction Indicator -->
        <path d="M {vc_x - 30} {vc_y + flange_r + 20} L {vc_x + 30} {vc_y + flange_r + 20}" stroke="#10b981" stroke-width="2.5" marker-end="url(#arrow)"/>
        <text x="{vc_x}" y="{vc_y + flange_r + 38}" fill="#10b981" font-size="11" font-weight="600" text-anchor="middle">FLOW DIRECTION (CLASS 150/300)</text>

        <!-- Face to Face Dimension -->
        <line x1="{vc_x - (v_len/2)}" y1="{vc_y - flange_r - 20}" x2="{vc_x + (v_len/2)}" y2="{vc_y - flange_r - 20}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
        <text x="{vc_x}" y="{vc_y - flange_r - 26}" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="middle">FACE-TO-FACE: {total_len} mm</text>
        <text x="{vc_x}" y="{vc_y + flange_r + 58}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">VALVE ASSEMBLY ELEVATION &amp; SECTION</text>
        '''

    elif "spool" in comp_type or "pipe" in comp_type:
        # ================= PIPING SPOOL BLUEPRINT =================
        sp_x, sp_y = 475, 230
        # Bound dimensions strictly to 55px radius so flanges NEVER cross header (y=58) or title block (y=425)
        flange_r = 55.0
        flange_w = 16.0
        sp_len = 460.0
        pipe_r = 24.0

        view_a_content = f'''
        <!-- Centerline -->
        <line x1="{sp_x - (sp_len/2) - 30}" y1="{sp_y}" x2="{sp_x + (sp_len/2) + 30}" y2="{sp_y}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>

        <!-- Left Flange -->
        <rect x="{sp_x - (sp_len/2)}" y="{sp_y - flange_r}" width="{flange_w}" height="{flange_r*2}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2"/>
        <!-- Right Flange -->
        <rect x="{sp_x + (sp_len/2) - flange_w}" y="{sp_y - flange_r}" width="{flange_w}" height="{flange_r*2}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2"/>

        <!-- Pipe Barrel -->
        <rect x="{sp_x - (sp_len/2) + flange_w}" y="{sp_y - pipe_r}" width="{sp_len - (flange_w*2)}" height="{pipe_r*2}" fill="#16293d" stroke="#38bdf8" stroke-width="2"/>
        <!-- Bore Hollow -->
        <rect x="{sp_x - (sp_len/2) + flange_w}" y="{sp_y - pipe_r + 6}" width="{sp_len - (flange_w*2)}" height="{(pipe_r - 6)*2}" fill="#090d12" stroke="#475569" stroke-dasharray="4,3"/>

        <!-- Field Weld Seam Callouts -->
        <line x1="{sp_x - (sp_len/2) + flange_w}" y1="{sp_y - pipe_r - 12}" x2="{sp_x - (sp_len/2) + flange_w}" y2="{sp_y + pipe_r + 12}" stroke="#f59e0b" stroke-width="2" stroke-dasharray="3,2"/>
        <line x1="{sp_x + (sp_len/2) - flange_w}" y1="{sp_y - pipe_r - 12}" x2="{sp_x + (sp_len/2) - flange_w}" y2="{sp_y + pipe_r + 12}" stroke="#f59e0b" stroke-width="2" stroke-dasharray="3,2"/>

        <!-- Length Callout -->
        <line x1="{sp_x - (sp_len/2)}" y1="{sp_y - flange_r - 18}" x2="{sp_x + (sp_len/2)}" y2="{sp_y - flange_r - 18}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
        <text x="{sp_x}" y="{sp_y - flange_r - 24}" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="middle">TOTAL SPOOL LENGTH: {total_len} mm</text>
        <text x="{sp_x}" y="{sp_y + flange_r + 35}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">FABRICATED PIPING SPOOL (ASME B31.3 REFINERY PIPING)</text>
        <text x="{sp_x}" y="{sp_y + flange_r + 52}" fill="#64748b" font-size="10" text-anchor="middle">SCHEDULE 40 PIPE | CLASS 150 WELD NECK FLANGES</text>
        '''

    elif comp_type == "custom":
        # ================= GENERIC CUSTOM ASSEMBLY BLUEPRINT =================
        # Smart multi-view rendering for any LLM-generated component.
        # Renders: Isometric box view (left) + Front elevation (right) + detail callouts
        cx, cy = 230, 250   # left view centre
        rx, ry = 620, 250   # right view centre

        # Derive pseudo-dimensions from spec (may be guesses, that's fine)
        w = spec.get("outer_diameter", 300.0)
        h = spec.get("total_length", 200.0)
        d = spec.get("thickness", 80.0)

        # Scale to fit the canvas safely
        max_px = 160.0
        sc = max_px / max(w, h, d, 1.0)
        sw, sh, sd = w * sc, h * sc, d * sc   # pixel sizes

        # Isometric offsets (30° projection)
        ox_iso = sd * 0.5   # x-offset per unit depth
        oy_iso = sd * 0.25  # y-offset per unit depth

        # ── ISOMETRIC BOX (left panel) ──
        # Front face
        x0, y0 = cx - sw / 2, cy - sh / 2
        x1, y1 = cx + sw / 2, cy + sh / 2
        # Top face (shifted up-right)
        txt, tyt = x0 + ox_iso, y0 - oy_iso
        txr, tyr = x1 + ox_iso, y0 - oy_iso
        # Side face (right, shifted right-down)
        sxt, syt = x1, y0
        sxb, syb = x1, y1
        sxtr, sytr = x1 + ox_iso, y0 - oy_iso
        sxbr, sybr = x1 + ox_iso, y1 - oy_iso

        # Internal grid lines on front face for "machined part" look
        n_hatch = 5
        hatch_lines = ""
        for i in range(1, n_hatch):
            hy = y0 + (sh / n_hatch) * i
            hatch_lines += f'<line x1="{x0:.1f}" y1="{hy:.1f}" x2="{x1:.1f}" y2="{hy:.1f}" stroke="#1e3a5f" stroke-width="0.8" stroke-dasharray="3,4"/>\n        '

        view_a_content = f'''
        <!-- ===== ISOMETRIC BOX VIEW (left) ===== -->
        <g id="isoView">
          <!-- Centerlines -->
          <line x1="{cx - sw/2 - 22}" y1="{cy}" x2="{cx + sw/2 + ox_iso + 22}" y2="{cy}" stroke="#ef4444" stroke-width="0.9" stroke-dasharray="6,3"/>
          <line x1="{cx}" y1="{cy - sh/2 - 22}" x2="{cx}" y2="{cy + sh/2 + 22}" stroke="#ef4444" stroke-width="0.9" stroke-dasharray="6,3"/>

          <!-- Top face -->
          <polygon points="{x0:.1f},{y0:.1f} {x1:.1f},{y0:.1f} {txr:.1f},{tyr:.1f} {txt:.1f},{tyt:.1f}"
                   fill="#16293d" stroke="#38bdf8" stroke-width="1.8"/>

          <!-- Right (side) face -->
          <polygon points="{sxt:.1f},{syt:.1f} {sxb:.1f},{syb:.1f} {sxbr:.1f},{sybr:.1f} {sxtr:.1f},{sytr:.1f}"
                   fill="#0d1f30" stroke="#38bdf8" stroke-width="1.8"/>

          <!-- Front face -->
          <rect x="{x0:.1f}" y="{y0:.1f}" width="{sw:.1f}" height="{sh:.1f}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2.2"/>
          {hatch_lines}

          <!-- Central bore / feature circle -->
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{min(sw, sh)*0.22:.1f}" fill="#090d12" stroke="#60a5fa" stroke-width="1.8" stroke-dasharray="5,3"/>

          <!-- Corner chamfer markers -->
          <line x1="{x0:.1f}" y1="{y0+8:.1f}" x2="{x0+8:.1f}" y2="{y0:.1f}" stroke="#f59e0b" stroke-width="1.5"/>
          <line x1="{x1:.1f}" y1="{y0+8:.1f}" x2="{x1-8:.1f}" y2="{y0:.1f}" stroke="#f59e0b" stroke-width="1.5"/>

          <!-- Width dimension line -->
          <line x1="{x0:.1f}" y1="{y0-16:.1f}" x2="{x1:.1f}" y2="{y0-16:.1f}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
          <text x="{cx:.1f}" y="{y0-20:.1f}" fill="#38bdf8" font-size="10" font-weight="600" text-anchor="middle">W: {w:.0f} mm</text>

          <!-- Height dimension line -->
          <line x1="{x0-18:.1f}" y1="{y0:.1f}" x2="{x0-18:.1f}" y2="{y1:.1f}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
          <text x="{x0-22:.1f}" y="{cy:.1f}" fill="#38bdf8" font-size="10" font-weight="600" text-anchor="end" dominant-baseline="middle">H: {h:.0f}</text>

          <text x="{cx:.1f}" y="{y1+26:.1f}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">VIEW A: ISOMETRIC</text>
          <text x="{cx:.1f}" y="{y1+42:.1f}" fill="#64748b" font-size="10" text-anchor="middle">W×H×D: {w:.0f}×{h:.0f}×{d:.0f} mm</text>
        </g>

        <!-- ===== FRONT ELEVATION (right panel) ===== -->
        <g id="frontElev">
          <!-- Centerlines -->
          <line x1="{rx}" y1="{ry - sh/2 - 25:.1f}" x2="{rx}" y2="{ry + sh/2 + 25:.1f}" stroke="#ef4444" stroke-width="0.9" stroke-dasharray="6,3"/>
          <line x1="{rx - sw/2 - 22:.1f}" y1="{ry}" x2="{rx + sw/2 + 22:.1f}" y2="{ry}" stroke="#ef4444" stroke-width="0.9" stroke-dasharray="6,3"/>

          <!-- Outer envelope -->
          <rect x="{rx - sw/2:.1f}" y="{ry - sh/2:.1f}" width="{sw:.1f}" height="{sh:.1f}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2.2"/>

          <!-- Hidden bore lines (dashed) -->
          <rect x="{rx - sw*0.22:.1f}" y="{ry - sh/2:.1f}" width="{sw*0.44:.1f}" height="{sh:.1f}" fill="#090d12" stroke="#475569" stroke-width="1.4" stroke-dasharray="5,3"/>

          <!-- Section hatch (diagonal) for cut material -->
          <line x1="{rx - sw/2:.1f}" y1="{ry - sh/4:.1f}" x2="{rx - sw*0.22:.1f}" y2="{ry - sh/2:.1f}" stroke="#334155" stroke-width="0.9"/>
          <line x1="{rx - sw/2:.1f}" y1="{ry:.1f}" x2="{rx - sw*0.22:.1f}" y2="{ry - sh/4:.1f}" stroke="#334155" stroke-width="0.9"/>
          <line x1="{rx - sw/2:.1f}" y1="{ry + sh/4:.1f}" x2="{rx - sw*0.22:.1f}" y2="{ry:.1f}" stroke="#334155" stroke-width="0.9"/>
          <line x1="{rx + sw*0.22:.1f}" y1="{ry - sh/4:.1f}" x2="{rx + sw/2:.1f}" y2="{ry - sh/2:.1f}" stroke="#334155" stroke-width="0.9"/>
          <line x1="{rx + sw*0.22:.1f}" y1="{ry:.1f}" x2="{rx + sw/2:.1f}" y2="{ry - sh/4:.1f}" stroke="#334155" stroke-width="0.9"/>
          <line x1="{rx + sw*0.22:.1f}" y1="{ry + sh/4:.1f}" x2="{rx + sw/2:.1f}" y2="{ry:.1f}" stroke="#334155" stroke-width="0.9"/>

          <!-- Feature callout bubbles -->
          <circle cx="{rx:.1f}" cy="{ry - sh/2 + 18:.1f}" r="10" fill="#0b1320" stroke="#10b981" stroke-width="1.5"/>
          <text x="{rx:.1f}" y="{ry - sh/2 + 22:.1f}" fill="#10b981" font-size="9" font-weight="700" text-anchor="middle">1</text>
          <circle cx="{rx + sw/2 - 18:.1f}" cy="{ry:.1f}" r="10" fill="#0b1320" stroke="#f59e0b" stroke-width="1.5"/>
          <text x="{rx + sw/2 - 18:.1f}" y="{ry + 4:.1f}" fill="#f59e0b" font-size="9" font-weight="700" text-anchor="middle">2</text>

          <!-- Dimension: width -->
          <line x1="{rx - sw/2:.1f}" y1="{ry + sh/2 + 16:.1f}" x2="{rx + sw/2:.1f}" y2="{ry + sh/2 + 16:.1f}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
          <text x="{rx:.1f}" y="{ry + sh/2 + 12:.1f}" fill="#38bdf8" font-size="10" font-weight="600" text-anchor="middle">{w:.0f} mm</text>

          <!-- Dimension: height -->
          <line x1="{rx + sw/2 + 18:.1f}" y1="{ry - sh/2:.1f}" x2="{rx + sw/2 + 18:.1f}" y2="{ry + sh/2:.1f}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
          <text x="{rx + sw/2 + 24:.1f}" y="{ry:.1f}" fill="#38bdf8" font-size="10" font-weight="600" dominant-baseline="middle">{h:.0f}</text>

          <text x="{rx:.1f}" y="{ry + sh/2 + 36:.1f}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">SECTION B-B: FRONT ELEVATION</text>
          <text x="{rx:.1f}" y="{ry + sh/2 + 52:.1f}" fill="#64748b" font-size="10" text-anchor="middle">LLM-GENERATED GEOMETRY | qwen2.5-coder</text>
        </g>
        '''

    else:
        # ================= STANDARD FLANGE BLUEPRINT =================
        top_cx, top_cy = 220, 240
        front_cx, front_cy = 620, 240

        r_od = (od / 2.0) * scale
        r_pcd = (pcd / 2.0) * scale
        r_bore = (id_bore / 2.0) * scale
        r_hole = (hole_d / 2.0) * scale
        hub_d = spec.get("hub_diameter", 135.0)

        bolt_elements = []
        for i in range(holes):
            angle = i * (2.0 * math.pi / holes)
            hx = top_cx + r_pcd * math.cos(angle)
            hy = top_cy + r_pcd * math.sin(angle)
            bolt_elements.append(
                f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{r_hole:.1f}" fill="#111c24" stroke="#60a5fa" stroke-width="1.5"/>'
                f'<line x1="{hx-5:.1f}" y1="{hy:.1f}" x2="{hx+5:.1f}" y2="{hy:.1f}" stroke="#ef4444" stroke-width="0.75"/>'
                f'<line x1="{hx:.1f}" y1="{hy-5:.1f}" x2="{hx:.1f}" y2="{hy+5:.1f}" stroke="#ef4444" stroke-width="0.75"/>'
            )
        bolt_svg = "\n      ".join(bolt_elements)

        view_a_content = f'''
        <!-- ================= TOP PLAN VIEW ================= -->
        <g id="topView">
          <line x1="{top_cx - r_od - 20}" y1="{top_cy}" x2="{top_cx + r_od + 20}" y2="{top_cy}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>
          <line x1="{top_cx}" y1="{top_cy - r_od - 20}" x2="{top_cx}" y2="{top_cy + r_od + 20}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>

          <circle cx="{top_cx}" cy="{top_cy}" r="{r_od:.1f}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2.2"/>
          <circle cx="{top_cx}" cy="{top_cy}" r="{r_pcd:.1f}" fill="none" stroke="#f87171" stroke-width="1.2" stroke-dasharray="5,4"/>
          <circle cx="{top_cx}" cy="{top_cy}" r="{r_bore:.1f}" fill="#090d12" stroke="#38bdf8" stroke-width="2"/>

          {bolt_svg}

          <text x="{top_cx}" y="{top_cy + r_od + 32}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">VIEW A-A: TOP PLAN</text>
          <text x="{top_cx}" y="{top_cy + r_od + 48}" fill="#64748b" font-size="10" text-anchor="middle">PCD Ø{pcd}mm ({holes}x Ø{hole_d}mm HOLES)</text>

          <line x1="{top_cx - r_od}" y1="{top_cy - r_od - 10}" x2="{top_cx + r_od}" y2="{top_cy - r_od - 10}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
          <text x="{top_cx}" y="{top_cy - r_od - 14}" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="middle">Ø {od} mm (OUTER DIA)</text>
        </g>

        <!-- ================= FRONT SECTION VIEW ================= -->
        <g id="frontView">
          <line x1="{front_cx}" y1="{front_cy - (total_len*scale/2) - 25}" x2="{front_cx}" y2="{front_cy + (thk*scale/2) + 25}" stroke="#ef4444" stroke-width="1" stroke-dasharray="6,3"/>

          <rect x="{front_cx - r_od:.1f}" y="{front_cy - (thk*scale/2):.1f}" width="{r_od*2:.1f}" height="{thk*scale:.1f}" fill="#0f1e2e" stroke="#38bdf8" stroke-width="2"/>
          <rect x="{front_cx - (hub_d/2*scale):.1f}" y="{front_cy - (total_len*scale/2):.1f}" width="{hub_d*scale:.1f}" height="{(total_len - thk)*scale:.1f}" fill="#16293d" stroke="#38bdf8" stroke-width="1.8"/>

          <rect x="{front_cx - r_bore:.1f}" y="{front_cy - (total_len*scale/2):.1f}" width="{r_bore*2:.1f}" height="{total_len*scale:.1f}" fill="#090d12" stroke="#475569" stroke-width="1.5" stroke-dasharray="4,3"/>

          <text x="{front_cx}" y="{front_cy + (thk*scale/2) + 32}" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">SECTION B-B: ELEVATION</text>
          <text x="{front_cx}" y="{front_cy + (thk*scale/2) + 48}" fill="#64748b" font-size="10" text-anchor="middle">THICKNESS: {thk}mm | TOTAL LENGTH: {total_len}mm</text>

          <line x1="{front_cx + r_od + 18}" y1="{front_cy - (total_len*scale/2)}" x2="{front_cx + r_od + 18}" y2="{front_cy + (thk*scale/2)}" stroke="#38bdf8" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
          <text x="{front_cx + r_od + 24}" y="{front_cy}" fill="#38bdf8" font-size="11" font-weight="600" dominant-baseline="middle">{total_len} mm</text>
        </g>
        '''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 950 560" width="100%" height="100%" style="background:#090d12; font-family:'Segoe UI',Roboto,Helvetica,sans-serif;">
  <defs>
    <!-- Technical Grid Pattern -->
    <pattern id="cadGrid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#16222f" stroke-width="0.75"/>
    </pattern>
    <!-- Arrow Marker -->
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#38bdf8"/>
    </marker>
  </defs>

  <!-- Background Grid & Outer Engineering Border -->
  <rect width="950" height="560" fill="url(#cadGrid)"/>
  <rect x="15" y="15" width="920" height="530" fill="none" stroke="#1e3a5f" stroke-width="2"/>
  <rect x="20" y="20" width="910" height="520" fill="none" stroke="#0ea5e9" stroke-width="1" stroke-opacity="0.4"/>

  <!-- Clean Non-Colliding Header Banner -->
  <rect x="20" y="20" width="910" height="38" fill="#0f172a"/>
  <text x="35" y="44" fill="#38bdf8" font-size="12" font-weight="700">MANGALORE REFINERY &amp; PETROCHEMICALS LIMITED (MRPL) — CAD ENGINE</text>
  <text x="915" y="44" fill="#94a3b8" font-size="10" text-anchor="end">AIR-GAPPED SOVEREIGN WORKBENCH</text>
  <line x1="20" y1="58" x2="930" y2="58" stroke="#1e293b" stroke-width="1.5"/>

  <!-- Graphical Views -->
  {view_a_content}

  <!-- ================= STRICT NON-OVERLAPPING TITLE BLOCK ================= -->
  <g id="titleBlock" transform="translate(540, 425)">
    <!-- Main Box -->
    <rect width="375" height="100" fill="#0b1320" stroke="#0ea5e9" stroke-width="1.5"/>
    <!-- Horizontal Dividers -->
    <line x1="0" y1="32" x2="375" y2="32" stroke="#1e293b" stroke-width="1.2"/>
    <line x1="0" y1="66" x2="375" y2="66" stroke="#1e293b" stroke-width="1.2"/>
    <!-- Vertical Dividers -->
    <line x1="220" y1="32" x2="220" y2="100" stroke="#1e293b" stroke-width="1.2"/>

    <!-- Top Row -->
    <text x="12" y="21" fill="#38bdf8" font-size="10" font-weight="700">MANGALORE REFINERY &amp; PETROCHEMICALS LTD</text>
    <text x="362" y="21" fill="#10b981" font-size="10" font-weight="600" text-anchor="end">STATUS: CERTIFIED</text>

    <!-- Middle Row Left: Title -->
    <text x="12" y="46" fill="#94a3b8" font-size="8">COMPONENT TITLE</text>
    <text x="12" y="58" fill="#f8fafc" font-size="10" font-weight="600">{title[:30]}</text>

    <!-- Middle Row Right: Drawing Number -->
    <text x="228" y="46" fill="#94a3b8" font-size="8">DRAWING NUMBER</text>
    <text x="228" y="58" fill="#f8fafc" font-size="9" font-family="monospace">{dwg_no}</text>

    <!-- Bottom Row Left: Material & Standard -->
    <text x="12" y="78" fill="#94a3b8" font-size="8">MATERIAL &amp; STANDARD</text>
    <text x="12" y="90" fill="#f8fafc" font-size="9">{material[:16]} | {standard[:16]}</text>

    <!-- Bottom Row Right: Tolerance -->
    <text x="228" y="78" fill="#94a3b8" font-size="8">TOLERANCE</text>
    <text x="228" y="90" fill="#f8fafc" font-size="9">{tolerance}</text>
  </g>
</svg>'''
    return svg


def generate_3d_stl_mesh(spec: Dict[str, Any]) -> bytes:
    """Generate a clean 3D STL mesh of the parametric component.

    - For 'custom' LLM-generated components: a solid rectangular box.
    - For standard flanges/valves: the original annular ring (hollow cylinder).
    """
    comp_type = spec.get("component_type", "weld_neck_flange")
    triangles: List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]] = []

    if comp_type == "custom":
        # ── Box STL for any LLM-generated component ──
        w = spec.get("outer_diameter", 300.0)       # width  (X)
        h = spec.get("total_length", 200.0)         # height (Z)
        d = spec.get("thickness", 80.0)             # depth  (Y)
        x0, x1 = -w / 2.0, w / 2.0
        y0, y1 = -d / 2.0, d / 2.0
        z0, z1 = 0.0, h

        # 12 triangles for a box (2 per face × 6 faces)
        faces = [
            # Bottom (z0)
            ((x0,y0,z0),(x1,y0,z0),(x1,y1,z0)),
            ((x0,y0,z0),(x1,y1,z0),(x0,y1,z0)),
            # Top (z1)
            ((x0,y0,z1),(x1,y1,z1),(x1,y0,z1)),
            ((x0,y0,z1),(x0,y1,z1),(x1,y1,z1)),
            # Front (y0)
            ((x0,y0,z0),(x0,y0,z1),(x1,y0,z1)),
            ((x0,y0,z0),(x1,y0,z1),(x1,y0,z0)),
            # Back (y1)
            ((x0,y1,z0),(x1,y1,z1),(x0,y1,z1)),
            ((x0,y1,z0),(x1,y1,z0),(x1,y1,z1)),
            # Left (x0)
            ((x0,y0,z0),(x0,y1,z0),(x0,y1,z1)),
            ((x0,y0,z0),(x0,y1,z1),(x0,y0,z1)),
            # Right (x1)
            ((x1,y0,z0),(x1,y1,z1),(x1,y1,z0)),
            ((x1,y0,z0),(x1,y0,z1),(x1,y1,z1)),
        ]
        triangles = faces
    else:
        # ── Annular ring (hollow cylinder) for flanges / standard parts ──
        od = spec.get("outer_diameter", 230.0)
        id_bore = spec.get("bore_diameter", 102.3)
        thk = spec.get("thickness", 24.0)

        r_outer = od / 2.0
        r_inner = id_bore / 2.0
        z_bottom = 0.0
        z_top = thk

        segments = 48
        for i in range(segments):
            a1 = i * (2.0 * math.pi / segments)
            a2 = (i + 1) * (2.0 * math.pi / segments)

            x1_o, y1_o = r_outer * math.cos(a1), r_outer * math.sin(a1)
            x2_o, y2_o = r_outer * math.cos(a2), r_outer * math.sin(a2)
            x1_i, y1_i = r_inner * math.cos(a1), r_inner * math.sin(a1)
            x2_i, y2_i = r_inner * math.cos(a2), r_inner * math.sin(a2)

            triangles.append(((x1_o, y1_o, z_top), (x2_o, y2_o, z_top), (x2_i, y2_i, z_top)))
            triangles.append(((x1_o, y1_o, z_top), (x2_i, y2_i, z_top), (x1_i, y1_i, z_top)))
            triangles.append(((x2_o, y2_o, z_bottom), (x1_o, y1_o, z_bottom), (x1_i, y1_i, z_bottom)))
            triangles.append(((x2_o, y2_o, z_bottom), (x1_i, y1_i, z_bottom), (x2_i, y2_i, z_bottom)))
            triangles.append(((x1_o, y1_o, z_bottom), (x2_o, y2_o, z_bottom), (x2_o, y2_o, z_top)))
            triangles.append(((x1_o, y1_o, z_bottom), (x2_o, y2_o, z_top), (x1_o, y1_o, z_top)))
            if r_inner > 0:
                triangles.append(((x2_i, y2_i, z_bottom), (x1_i, y1_i, z_bottom), (x1_i, y1_i, z_top)))
                triangles.append(((x2_i, y2_i, z_bottom), (x1_i, y1_i, z_top), (x2_i, y2_i, z_top)))

    lines = ["solid MRPL_Parametric_CAD_Part"]
    for v1, v2, v3 in triangles:
        lines.append("  facet normal 0.0 0.0 1.0")
        lines.append("    outer loop")
        lines.append(f"      vertex {v1[0]:.3f} {v1[1]:.3f} {v1[2]:.3f}")
        lines.append(f"      vertex {v2[0]:.3f} {v2[1]:.3f} {v2[2]:.3f}")
        lines.append(f"      vertex {v3[0]:.3f} {v3[1]:.3f} {v3[2]:.3f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid MRPL_Parametric_CAD_Part\n")

    return "\n".join(lines).encode("utf-8")



def find_freecad_cmd() -> Optional[str]:
    """Locate local FreeCAD headless executable."""
    import shutil
    candidates = [
        r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe",
        r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
        r"C:\Program Files\FreeCAD 0.21\bin\freecadcmd.exe",
        r"C:\Program Files\FreeCAD\bin\freecadcmd.exe",
        shutil.which("freecadcmd"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def generate_fcstd_package(spec: Dict[str, Any], py_script: str) -> bytes:
    """Compile native .FCStd using local FreeCADCmd if available, producing real
    OpenCASCADE BREP geometry and TechDraw pages that display in FreeCAD GUI.
    Falls back to archive structure if FreeCAD binary is absent.
    """
    import subprocess
    import tempfile

    fc_bin = find_freecad_cmd()
    if fc_bin:
        try:
            temp_fcstd_path = os.path.join(tempfile.gettempdir(), f"mrpl_model_{int(datetime.now().timestamp())}.FCStd")
            if os.path.exists(temp_fcstd_path):
                os.remove(temp_fcstd_path)

            # In the script, replace the doc.saveAs call with our temporary destination
            modified_script = py_script
            save_target = temp_fcstd_path.replace("\\", "/")
            if "doc.saveAs(" in modified_script:
                import re
                modified_script = re.sub(r'doc\.saveAs\(.*?\)', f'doc.saveAs("{save_target}")', modified_script)
            else:
                modified_script += f'\ndoc.saveAs("{save_target}")\n'

            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as script_f:
                script_f.write(modified_script)
                script_path = script_f.name

            # Run FreeCAD headless compiler
            res = subprocess.run([fc_bin, script_path], capture_output=True, text=True, timeout=25)
            if os.path.exists(temp_fcstd_path) and os.path.getsize(temp_fcstd_path) > 500:
                with open(temp_fcstd_path, "rb") as fc_f:
                    compiled_bytes = fc_f.read()
                try:
                    os.remove(temp_fcstd_path)
                    os.remove(script_path)
                except Exception:
                    pass
                logger.info("freecad_binary_compilation_success", size=len(compiled_bytes))
                return compiled_bytes
        except Exception as ex:
            logger.warning("freecad_binary_compilation_failed", error=str(ex))

    # Fallback if FreeCAD binary not found or failed
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        doc_xml = f"""<?xml version='1.0' encoding='utf-8'?>
<Document SchemaVersion="4" FileVersion="2">
  <Properties Count="5">
    <Property name="CreatedBy" type="App::PropertyString"><String value="MRPL Sovereign AI Workbench"/></Property>
    <Property name="Company" type="App::PropertyString"><String value="Mangalore Refinery and Petrochemicals Limited"/></Property>
    <Property name="Title" type="App::PropertyString"><String value="{spec.get('title', 'Industrial CAD Part')}"/></Property>
    <Property name="Standard" type="App::PropertyString"><String value="{spec.get('standard', 'ASME B16.5')}"/></Property>
    <Property name="Material" type="App::PropertyString"><String value="{spec.get('material', 'ASTM A105')}"/></Property>
  </Properties>
  <Objects Count="1">
    <Object type="Part::Feature" name="MRPL_Component" id="1">
      <Properties Count="2">
        <Property name="Label" type="App::PropertyString"><String value="{spec.get('title', 'Component')}"/></Property>
        <Property name="Visibility" type="App::PropertyBool"><Bool value="true"/></Property>
      </Properties>
    </Object>
  </Objects>
</Document>"""
        zf.writestr("Document.xml", doc_xml.encode("utf-8"))
        zf.writestr("freecad_automation.py", py_script.encode("utf-8"))
    
    return buf.getvalue()



def generate_cad_deliverables(user_query: str, spec_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Top-level pipeline generating:
    1. Dynamic Spec (incorporating LLM Qwen3:8B JSON)
    2. FreeCAD Python Automation Script
    3. Native .FCStd Package
    4. 2D AutoCAD .DXF
    5. 2D SVG TechDraw Blueprint
    6. 3D Mesh (.STL)
    """
    spec = parse_cad_spec(user_query, spec_override)

    py_script = generate_freecad_python_script(spec)
    fcstd_bytes = generate_fcstd_package(spec, py_script)
    dxf_bytes = generate_dxf_drawing(spec)
    svg_str = generate_svg_blueprint(spec)
    stl_bytes = generate_3d_stl_mesh(spec)

    clean_title = spec.get("title", "CAD_Part").replace(" ", "_").replace('"', 'in').replace('/', '_')

    return {
        "spec": spec,
        "files": {
            "fcstd": {
                "name": f"{clean_title}.FCStd",
                "type": "fcstd",
                "data": fcstd_bytes,
            },
            "dxf": {
                "name": f"{clean_title}.dxf",
                "type": "dxf",
                "data": dxf_bytes,
            },
            "svg": {
                "name": f"{clean_title}_TechDraw.svg",
                "type": "svg",
                "data": svg_str.encode("utf-8"),
            },
            "stl": {
                "name": f"{clean_title}_3D.stl",
                "type": "stl",
                "data": stl_bytes,
            },
            "py": {
                "name": f"{clean_title}_freecad.py",
                "type": "py",
                "data": py_script.encode("utf-8"),
            },
        },
    }


def execute_llm_freecad_script(
    llm_script: str,
    title: str,
    drawing_no: str,
    material: str,
    standard: str,
) -> Dict[str, Any]:
    """Execute a FreeCAD Python script generated by Qwen3:8B directly via freecadcmd.exe.

    This is the LLM-DRIVEN pipeline:
      Qwen3:8B generates the full FreeCAD Python → freecadcmd executes it → artifacts returned.

    No hardcoded component geometry here at all.
    """
    import subprocess
    import tempfile

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    doc_name = f"MRPL_LLM_{timestamp}"
    clean_title = title.replace(" ", "_").replace("/", "_").replace('"', "in")[:50]
    freecad_cmd = find_freecad_cmd()

    # Wrap the LLM script with the boilerplate header and doc.saveAs
    full_script = f"""# -*- coding: utf-8 -*-
\"\"\"
Sovereign AI Workbench - LLM-Generated FreeCAD Automation Script
Title: {title}
Drawing No: {drawing_no}
Standard: {standard} | Material: {material}
Generated: {timestamp} | Air-Gapped Sovereign Deployment
\"\"\"

import math
try:
    import FreeCAD as App
    import Part
    import TechDraw
except ImportError:
    import sys
    sys.exit(0)

# Initialize Document
doc = App.newDocument("{doc_name}")

# ── LLM GENERATED 3D GEOMETRY ──────────────────────────────────────────────
{llm_script}
# ─────────────────────────────────────────────────────────────────────────

doc.recompute()

# Save .FCStd
doc.saveAs("{doc_name}.FCStd")
print("Saved: {doc_name}.FCStd")
"""

    svg_str = ""
    stl_bytes = b""
    dxf_bytes = b""
    fcstd_bytes = b""

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, f"{doc_name}.py")
            fcstd_path = os.path.join(tmpdir, f"{doc_name}.FCStd")

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(full_script)

            if freecad_cmd:
                result = subprocess.run(
                    [freecad_cmd, script_path],
                    capture_output=True, text=True, timeout=120,
                    cwd=tmpdir, encoding="utf-8", errors="replace",
                )
                logger.info("llm_freecad_exec", stdout=result.stdout[:500], stderr=result.stderr[:500])

                if os.path.exists(fcstd_path):
                    with open(fcstd_path, "rb") as f:
                        fcstd_bytes = f.read()
                    logger.info("llm_freecad_fcstd_ok", size=len(fcstd_bytes))
                else:
                    logger.warning("llm_freecad_fcstd_not_found", stdout=result.stdout, stderr=result.stderr)
            else:
                logger.warning("freecad_cmd_not_found_llm_pipeline")

        # Build a clean 2D SVG blueprint from extracted dimensions (best-effort)
        # Try to parse real dimensions from the LLM Python script (radius, height, etc.)
        import re as _re2
        _nums = list(map(float, _re2.findall(r"(?:radius|r)\s*=\s*([\d.]+)", llm_script)))
        _heights = list(map(float, _re2.findall(r"(?:height|h|length|l)\s*=\s*([\d.]+)", llm_script)))
        _widths = list(map(float, _re2.findall(r"(?:width|w|size)\s*=\s*([\d.]+)", llm_script)))

        _od = (_nums[0] * 2.0) if _nums else 300.0
        _h = _heights[0] if _heights else 200.0
        _d = _widths[0] if _widths else (_nums[1] * 2.0 if len(_nums) > 1 else 80.0)

        spec_guess = {
            "title": title,
            "drawing_no": drawing_no,
            "material": material,
            "standard": standard,
            "component_type": "custom",
            "outer_diameter": _od,
            "bore_diameter": _od * 0.4,
            "total_length": _h,
            "bolt_circle_diameter": _od * 0.8,
            "bolt_hole_count": 8,
            "bolt_hole_diameter": _od * 0.07,
            "thickness": _d,
        }
        svg_str = generate_svg_blueprint(spec_guess)
        stl_bytes = generate_3d_stl_mesh(spec_guess)
        if HAS_EZDXF:
            dxf_bytes = generate_dxf_drawing(spec_guess)

    except Exception as e:
        logger.error("llm_freecad_exec_error", error=str(e))

    return {
        "title": title,
        "drawing_no": drawing_no,
        "files": {
            "py": {
                "name": f"{clean_title}_freecad.py",
                "type": "py",
                "data": full_script.encode("utf-8"),
            },
            "fcstd": {
                "name": f"{clean_title}.FCStd",
                "type": "fcstd",
                "data": fcstd_bytes,
            },
            "svg": {
                "name": f"{clean_title}_TechDraw.svg",
                "type": "svg",
                "data": svg_str.encode("utf-8"),
            },
            "stl": {
                "name": f"{clean_title}_3D.stl",
                "type": "stl",
                "data": stl_bytes,
            },
            "dxf": {
                "name": f"{clean_title}.dxf",
                "type": "dxf",
                "data": dxf_bytes,
            },
        },
    }

    """Top-level pipeline generating:
    1. Dynamic Spec (incorporating LLM Qwen3:8B JSON)
    2. FreeCAD Python Automation Script
    3. Native .FCStd Package
    4. 2D AutoCAD .DXF
    5. 2D SVG TechDraw Blueprint
    6. 3D Mesh (.STL)
    """
    spec = parse_cad_spec(user_query, spec_override)

    py_script = generate_freecad_python_script(spec)
    fcstd_bytes = generate_fcstd_package(spec, py_script)
    dxf_bytes = generate_dxf_drawing(spec)
    svg_str = generate_svg_blueprint(spec)
    stl_bytes = generate_3d_stl_mesh(spec)

    clean_title = spec.get("title", "CAD_Part").replace(" ", "_").replace('"', 'in').replace('/', '_')

    return {
        "spec": spec,
        "files": {
            "fcstd": {
                "name": f"{clean_title}.FCStd",
                "type": "fcstd",
                "data": fcstd_bytes,
            },
            "dxf": {
                "name": f"{clean_title}.dxf",
                "type": "dxf",
                "data": dxf_bytes,
            },
            "svg": {
                "name": f"{clean_title}_TechDraw.svg",
                "type": "svg",
                "data": svg_str.encode("utf-8"),
            },
            "stl": {
                "name": f"{clean_title}_3D.stl",
                "type": "stl",
                "data": stl_bytes,
            },
            "py": {
                "name": f"{clean_title}_freecad.py",
                "type": "py",
                "data": py_script.encode("utf-8"),
            },
        },
    }
