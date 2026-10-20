# CAD Skill — 3D Parametric CAD Modeling & 2D Engineering Blueprints

## Purpose
Enables autonomous generation of industrial 3D solid models and 2D engineering blueprints using headless FreeCAD automation and local AI reasoning. Produces native `.FCStd` projects, AutoCAD `.DXF` drawings, vector `.SVG` blueprints, and `.STL` meshes compliant with ASME Section VIII/B16.5 and IBR 1950 standards.

## Execution Rules
1. Reason over mechanical and dimensional requirements using local Qwen reasoning models.
2. Utilize the FreeCAD Part workbench primitives (`Part.makeCylinder`, `Part.makeBox`, `Part.makeSphere`, `.fuse()`, `.cut()`).
3. Compile 5 air-gapped deliverables: `.FCStd`, `.DXF`, `.SVG`, `.STL`, and `.py`.
4. Register all generated files into the Sovereign Artifact Vault for instant preview and download.
