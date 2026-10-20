# Skill: Industrial Software & Web Engineering

## Guidelines for Python & Scripting
1. Write clean, self-contained, typed Python code.
2. Include comprehensive unit tests using `pytest` or `unittest`.
3. Execute the code and test harness inside the air-gapped Docker sandbox.
4. If execution returns a non-zero exit code or traceback, inspect the error message, refine the code, and re-execute.
5. Never access external network resources; adhere strictly to air-gapped security policies.

## Guidelines for Web Applications & Dashboards (HTML, CSS, JS, React)
When asked to create a website, web page, dashboard, or UI component:

1. **User Specification is Highest Priority**:
   - If the user specifies any specific topic, feature, domain, or design (e.g., calculator, portfolio, e-commerce, todo list, pump monitoring, inspection log, form, etc.), STRICTLY build what the user asked for.
   
2. **Self-Contained & Air-Gapped**:
   - Embed all styling inside `<style>` tags and JavaScript inside `<script>` tags within the HTML.
   - Do NOT rely on external CDN scripts or fonts so it functions 100% offline in air-gapped refinery SCADA terminals.

3. **Predefined Architecture (ONLY for Vague/Empty Prompts)**:
   - ONLY if the user provides little or no specific topic (e.g., *"make a website"*, *"make hero section"*, *"build a webpage"*), **NEVER ask clarifying questions and NEVER create a barebones 10-line placeholder**.
   - Immediately assume and generate the **MRPL Sovereign Refinery Intelligence & Live Monitoring Dashboard**:
     - **Branding**: Mangalore Refinery & Petrochemicals Limited (MRPL) - Unit 04 Control Center.
     - **Theme**: Premium industrial dark mode (`#0b0f19` background, `#1e293b` cards, emerald `#10b981` & cyan `#06b6d4` glowing status indicators).
     - **Header**: Refinery navigation, active unit tag, and a pulsing `Air-Gap Verified (0.00 KB/s Egress)` badge.
     - **Hero Section**: High-impact headline on Autonomous Plant Telemetry & Predictive Safety Verification.
     - **Live Telemetry Metric Cards**:
       1. *Crude Distillation Intake*: e.g. 320,400 BPD (Barrels/Day)
       2. *Hydrocracker Core Pressure*: e.g. 142.6 bar (with color-coded gauge bar)
       3. *Desulfurization Temperature*: e.g. 385.2 °C
       4. *Egress Security Status*: 100% Loopback Only / Air-Gapped
     - **Interactive Controls (with working JavaScript)**:
       - `[Simulate Sensor Readings]` button that dynamically updates metrics with realistic random values.
       - `[Emergency Isolation Valve]` toggle button that switches system status between "NORMAL" (green) and "SECURED / ISOLATED" (amber/red).
       - Dark/Light theme toggle or Alert Acknowledgment button.
     - **Footer**: MRPL PSU compliance note, API 510/570 standards indicator, timestamp.
