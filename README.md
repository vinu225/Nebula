# Sovereign On-Premise Agentic AI Workbench (SIH26117)

**For Confidential Industrial Knowledge Work at Refineries, PSUs, and Defense-Linked Units**

---

## 1. Executive Summary

Refineries (e.g. MRPL), PSUs, and defense establishments generate sensitive knowledge work:
- Ultrasonic thickness measurement (UTM) inspection sheets
- Piping & Instrumentation Diagrams (P&IDs)
- Formal government approval notes and board memorandums
- Proprietary internal scripts and engineering calculations

Corporate security policy strictly forbids uploading this confidential IP to cloud AI providers. **Sovereign AI Workbench** provides a **100% on-premise, air-gapped agentic AI platform** powered by open-weight multimodal LLMs, local vector RAG, sandboxed code execution, and formal document generators.

---

## 2. Key Architecture Pillars

| Component | Technology | Purpose |
|---|---|---|
| **Agent Orchestration** | LangGraph StateGraph | Multi-step autonomous planning, execution, and verification |
| **Model Serving** | Ollama / vLLM | Open-weight models (`qwen3.5:4b`, `qwen3:8b`, `qwen3-vl:8b`, `qwen2.5-coder:8b`) |
| **Request & Model Router** | Fast Heuristic Classifier + Capability Matcher | Routes casual chat to 4B, reasoning to 8B, P&ID scans to 8B-VL, and coding to 8B-Coder |
| **Document Processing & OCR** | PyMuPDF, PDFPlumber, pytesseract, EasyOCR | Ingests digital PDFs and scanned inspection drawings |
| **Native Document Gen** | `python-docx`, `python-pptx`, `openpyxl`, ReportLab | Generates official Indian PSU-standard `.docx` Approval Notes, `.pptx` presentations, and `.xlsx` models |
| **Local Vector RAG** | PostgreSQL 16 + pgvector, hybrid BM25 + dense RRF | Semantic retrieval over refinery manuals and OISD/API standards |
| **Air-gapped Code Sandbox** | Docker with `--network=none` + AST security validator | Runs Python analysis scripts isolated with zero internet access |
| **Protocol Integration** | Model Context Protocol (MCP) | Sandboxed filesystem and execution tools |
| **Audit & Sovereignty** | Structlog + PostgreSQL + Network Monitor | Proves zero data egress and logs every model/tool action |
| **Frontend Workbench** | Next.js 15, React, Tailwind CSS | Real-time SSE streaming, agent traces, security dashboard |

---

## 3. Supported Industrial Skills

Discovered dynamically from `/skills`:
1. `document_analysis`: Technical memo and specification analysis with page-level citations.
2. `inspection_report`: Refinery equipment NDT/UTM report processing, anomaly flagging, and API 510/570 code verification.
3. `approval_note`: Generates formatted Indian PSU / MRPL Approval Notes in `.docx`.
4. `coding`: Industrial Python script development, test execution, and automatic error recovery in Docker sandbox.
5. `pid_analysis`: Multimodal analysis of P&ID drawings, ISA-5.1 instrument tags, and HAZOP hazard checks.
6. `knowledge_research`: Local hybrid dense + sparse search over plant SOPs and operating manuals.
7. `spreadsheet_analysis`: Refinery crude intake, yield, and off-spec product logs.

---

## 4. Sovereignty & Air-Gap Guarantees

- **Zero Cloud LLM Calls**: Operates without OpenAI, Anthropic, or external APIs.
- **Zero Cloud Vector DBs**: pgvector runs entirely on localhost / private docker network.
- **Strict Outbound Network Interception**: The `NetworkMonitor` validates and blocks all non-loopback connections.
- **Docker Sandbox Hardening**: Code execution containers run with `--network=none`, `256MB` RAM limit, `1 CPU` quota, and read-only mounts.

---

## 5. Quick Start

### Prerequisites
- Docker & Docker Compose
- NVIDIA GPU with 8GB+ VRAM (or CPU fallback for testing)
- [Ollama](https://ollama.ai) installed locally (if running outside Docker)

### Option A: Run Full Stack with Docker Compose
```bash
docker-compose up --build
```
- **Workbench UI**: `http://localhost:3000`
- **FastAPI Docs**: `http://localhost:8000/docs`
- **MinIO Console**: `http://localhost:9001` (minioadmin / minioadmin)

### Option B: Local Development

**1. Backend**:
```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Run Backend Tests**:
```bash
cd backend
uv run pytest
```

**3. Frontend**:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 6. Demo Workflows

### Workflow 1: Scanned Inspection Report to Formal Approval Note
1. Upload an inspection report PDF containing ultrasonic thickness test readings.
2. The agent triggers OCR/PDF parser and identifies thinning below Minimum Retirement Thickness (MRT).
3. The agent retrieves the relevant API 570 / OISD standards via local pgvector RAG.
4. The agent generates a formal `Approval_Note_MRPL.docx` with Background, Technical Rationale, Financial Implication, and Recommendation sections ready for download.

### Workflow 2: Coding Agent in Isolated Sandbox
1. Request: "Write a script to compute refinery heat exchanger log mean temperature difference (LMTD) with unit tests."
2. The agent routes to `qwen2.5-coder:8b`.
3. Code is validated by the AST security parser and executed inside the Docker sandbox (`--network=none`).
4. Output and passing test reports are presented in the real-time agent trace.

### Workflow 3: P&ID Diagram Vision Inspection
1. Attach a piping and instrumentation diagram image.
2. The Request Router detects visual drawing input and routes to `qwen3-vl:8b`.
3. The model extracts instrument loops (PT, TT, FT, PCV), safety relief valves (PSV), and highlights uninstrumented lines.
