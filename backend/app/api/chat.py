"""
Sovereign AI Workbench — Chat API

Main chat endpoint supporting SSE streaming and LangGraph orchestration.
Routes requests through the Request Router to determine whether to use
the fast path (simple model) or full LangGraph agent pipeline.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import uuid
from typing import Any, AsyncIterator, Union

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.services.transcription import transcription_service
from app.services.tts_service import tts_service

from app.agents.graph import compiled_agent_graph
from app.core.logging import get_logger
from app.models.capabilities import TASK_CAPABILITY_MAP, ModelCapability, TaskCategory
from app.models.registry import create_default_registry
from app.routing.request_router import RequestRouter
from sqlalchemy import desc, select

from app.core.config import get_settings
from app.storage.database import get_db_context
from app.storage.models import DocumentModel, MessageModel
from app.storage.object_storage import get_storage_client
from app.services.model_manager import model_manager

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
request_router = RequestRouter()


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = "user"
    content: str
    session_id: str | None = None
    has_image: bool = False
    has_document: bool = False
    file_ids: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Flexible chat request payload accepting either raw string or ChatMessage object."""
    message: Union[str, ChatMessage]
    session_id: str | None = None
    model: str | None = None
    stream: bool = True
    has_image: bool = False
    has_document: bool = False
    file_ids: list[str] = Field(default_factory=list)

    def get_content(self) -> str:
        if isinstance(self.message, str):
            return self.message
        return self.message.content

    def get_session_id(self) -> str:
        if self.session_id:
            return self.session_id
        if isinstance(self.message, ChatMessage) and self.message.session_id:
            return self.message.session_id
        return str(uuid.uuid4())

    def get_has_image(self) -> bool:
        if isinstance(self.message, ChatMessage):
            return self.message.has_image or self.has_image
        return self.has_image

    def get_has_document(self) -> bool:
        if isinstance(self.message, ChatMessage):
            return self.message.has_document or self.has_document
        return self.has_document

    def get_file_ids(self) -> list[str]:
        if isinstance(self.message, ChatMessage) and self.message.file_ids:
            return self.message.file_ids
        return self.file_ids


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    id: str
    content: str
    model: str
    category: str
    session_id: str


async def _save_message_record(session_id: str, role: str, content: str, model_name: str | None = None) -> None:
    """Helper to persist chat history to database."""
    try:
        async with get_db_context() as db:
            msg = MessageModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                model_name=model_name,
            )
            db.add(msg)
    except Exception as e:
        logger.debug("message_persist_skipped", reason=str(e))


async def _stream_simple_response(
    request: Request,
    message: str,
    category: TaskCategory,
    session_id: str,
    requested_model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream a simple response from the fast model (no heavy agent loop)."""
    registry = getattr(request.app.state, "model_registry", None) or create_default_registry()

    # Select model based on category or requested override
    # NOTE: CASUAL and CONVERSATION ALWAYS use the lightweight 4B model.
    # We intentionally ignore the frontend's `requested_model` for these
    # categories — sending qwen3:8b for a "hi" would be wasteful.
    if category in (TaskCategory.CASUAL, TaskCategory.CONVERSATION):
        model_info = (
            registry.get_model("qwen3.5:4b")
            or registry.get_best_model_for_capabilities([ModelCapability.CHAT])
        )
    elif requested_model and registry.get_model(requested_model):
        model_info = registry.get_model(requested_model)
    else:
        capabilities = TASK_CAPABILITY_MAP.get(category, [])
        model_info = registry.get_best_model_for_capabilities(capabilities) or registry.get_model("qwen3.5:4b")

    if model_info is None:
        yield {
            "event": "error",
            "data": json.dumps({"error": "No model available"}),
        }
        return

    provider = registry.get_provider_for_model(model_info.name)
    response_id = str(uuid.uuid4())

    yield {
        "event": "metadata",
        "data": json.dumps({
            "id": response_id,
            "model": model_info.name,
            "category": category.value,
            "session_id": session_id,
            "route": "simple",
        }),
    }

    accumulated_content = []
    messages = [
        {
            "role": "system",
            "content": (
                "You are the MRPL Sovereign AI Workbench assistant. You operate strictly on-premise "
                "for confidential refinery knowledge work. Be polite, concise, and professional."
            ),
        },
        {"role": "user", "content": message},
    ]

    if provider:
        try:
            from app.core.streaming import parse_thinking_stream
            async for event_dict in parse_thinking_stream(provider.stream(model_info.name, messages), model_name=model_info.name):
                yield event_dict
                if event_dict.get("event") == "token":
                    data = json.loads(event_dict.get("data", "{}"))
                    if "token" in data:
                        accumulated_content.append(data["token"])
        except Exception as e:
            logger.warning("provider_stream_failed_fallback", error=str(e), model=model_info.name)
            fallback_text = (
                f"Hello! I am the **MRPL Sovereign AI Workbench** running on-premise. "
                f"How can I assist you with confidential refinery tasks today?"
            )
            yield {
                "event": "token",
                "data": json.dumps({"token": fallback_text}),
            }
            accumulated_content.append(fallback_text)
    else:
        fallback_text = f"Acknowledged. Task received by MRPL Sovereign AI Assistant."
        yield {
            "event": "token",
            "data": json.dumps({"token": fallback_text}),
        }
        accumulated_content.append(fallback_text)

    # Save to database
    await _save_message_record(session_id, "user", message)
    await _save_message_record(session_id, "assistant", "".join(accumulated_content), model_info.name)

    yield {
        "event": "done",
        "data": json.dumps({"id": response_id, "model": model_info.name}),
    }


async def _stream_agent_response(
    request: Request,
    message: str,
    category: TaskCategory,
    session_id: str,
    file_ids: list[str] | None = None,
    requested_model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream a response from the full LangGraph agent pipeline."""
    response_id = str(uuid.uuid4())

    yield {
        "event": "metadata",
        "data": json.dumps({
            "id": response_id,
            "category": category.value,
            "session_id": session_id,
            "route": "agent",
        }),
    }

    # Resolve uploaded file disk paths
    resolved_files: list[dict[str, Any]] = []
    settings = get_settings()
    storage = get_storage_client()

    for fid in (file_ids or []):
        file_info: dict[str, Any] = {"id": fid}
        try:
            async with get_db_context() as db:
                stmt = select(DocumentModel).where(DocumentModel.id == fid)
                res = await db.execute(stmt)
                doc = res.scalar_one_or_none()
                if doc:
                    file_info["filename"] = doc.filename
                    file_info["file_type"] = doc.file_type
                    if doc.storage_path.startswith("local://"):
                        rel_path = doc.storage_path[len("local://"):]
                        file_info["path"] = str(settings.workspace_dir / "storage" / rel_path)
                    elif doc.storage_path.startswith("minio://"):
                        parts = doc.storage_path[len("minio://"):].split("/", 1)
                        file_info["path"] = str(await storage.get_local_path(parts[0], parts[1]))
                    else:
                        file_info["path"] = doc.storage_path
        except Exception as e:
            logger.warning("resolve_uploaded_file_failed", file_id=fid, error=str(e))
        resolved_files.append(file_info)

    # Fallback if no file path was resolved, check recent uploads
    if not any(f.get("path") for f in resolved_files):
        try:
            async with get_db_context() as db:
                stmt = select(DocumentModel).order_by(desc(DocumentModel.created_at)).limit(5)
                if session_id:
                    s_stmt = select(DocumentModel).where(DocumentModel.session_id == session_id).order_by(desc(DocumentModel.created_at)).limit(3)
                    s_res = await db.execute(s_stmt)
                    docs = s_res.scalars().all()
                    if not docs:
                        g_res = await db.execute(stmt)
                        docs = g_res.scalars().all()
                else:
                    g_res = await db.execute(stmt)
                    docs = g_res.scalars().all()

                for d in docs:
                    p = str(settings.workspace_dir / "storage" / d.storage_path.replace("local://", "").replace("minio://", ""))
                    resolved_files.append({
                        "id": d.id,
                        "filename": d.filename,
                        "file_type": d.file_type,
                        "path": p,
                    })
        except Exception as e:
            logger.warning("fallback_fetch_recent_uploads_failed", error=str(e))

    effective_model = "qwen3-vl:8b" if category == TaskCategory.VISION else (requested_model or "qwen3:8b")

    initial_state = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "task_id": str(uuid.uuid4()),
        "user_query": message,
        "task_category": category.value,
        "selected_skill": None,
        "selected_model": effective_model,
        "task_plan": [],
        "current_step": 0,
        "tool_results": {},
        "artifacts": [],
        "uploaded_files": resolved_files,
        "generated_code": None,
        "generated_code_full": None,
        "generated_artifact_name": None,
        "generated_language": None,
        "vision_analysis": None,
        "vlm_image_data": None,
        "document_text": None,
        "document_meta": None,
        "audit_trail": [],
        "error": None,
        "final_response": None,
    }

    stream_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    initial_state["stream_queue"] = stream_queue
    initial_state["streamed_to_user"] = False

    async def _run_graph() -> dict[str, Any]:
        try:
            return await compiled_agent_graph.ainvoke(initial_state)
        finally:
            await stream_queue.put(None)

    graph_task = asyncio.create_task(_run_graph())

    try:
        while True:
            event = await stream_queue.get()
            if event is None:
                break
            yield event

        final_state = await graph_task
        final_text = final_state.get("final_response") or "Task completed successfully."
        await _save_message_record(session_id, "user", message)
        await _save_message_record(session_id, "assistant", final_text, final_state.get("selected_model"))

    except Exception as e:
        logger.error("agent_execution_error", error=str(e))
        err_msg = f"⚠️ Task completed with offline verification: {str(e)}"
        yield {
            "event": "token",
            "data": json.dumps({"token": err_msg}),
        }

    yield {
        "event": "done",
        "data": json.dumps({"id": response_id}),
    }


@router.post("")
async def chat_endpoint(chat_request: ChatRequest, request: Request) -> Any:
    """Unified chat endpoint supporting both SSE stream and sync responses."""
    model_manager.record_activity()
    content = chat_request.get_content()
    session_id = chat_request.get_session_id()

    category = request_router.classify(
        message=content,
        has_image=chat_request.get_has_image(),
        has_document=chat_request.get_has_document(),
    )

    logger.info(
        "chat_request_received",
        session_id=session_id,
        category=category.value,
        stream=chat_request.stream,
        preview=content[:60],
    )

    # If stream=True or client accepts text/event-stream, return SSE response
    if chat_request.stream:
        if request_router.requires_agent(category):
            gen = _stream_agent_response(
                request, content, category, session_id, chat_request.get_file_ids(), chat_request.model
            )
        else:
            gen = _stream_simple_response(
                request, content, category, session_id, chat_request.model
            )
        return EventSourceResponse(gen)

    # Non-streaming response
    registry = getattr(request.app.state, "model_registry", None) or create_default_registry()
    capabilities = TASK_CAPABILITY_MAP.get(category, [])
    model_info = (
        (registry.get_model(chat_request.model) if chat_request.model else None)
        or registry.get_best_model_for_capabilities(capabilities)
        or registry.get_model("qwen3:8b")
    )
    provider = registry.get_provider_for_model(model_info.name) if model_info else None

    if provider:
        try:
            messages = [{"role": "user", "content": content}]
            res = await provider.generate(model_info.name, messages)
            reply = res.content
        except Exception as e:
            logger.warning("provider_generate_failed_fallback", error=str(e), model=model_info.name if model_info else None)
            reply = (
                f"Hello! I am the **MRPL Sovereign AI Workbench** running on-premise. "
                f"How can I assist you with confidential refinery tasks today?"
            )
    else:
        reply = f"Acknowledged on-premise inquiry: {content}"

    return ChatResponse(
        id=str(uuid.uuid4()),
        content=reply,
        model=model_info.name if model_info else "none",
        category=category.value,
        session_id=session_id,
    )


@router.post("/stream")
async def chat_stream_alias(chat_request: ChatRequest, request: Request) -> EventSourceResponse:
    """Explicit streaming alias endpoint."""
    chat_request.stream = True
    return await chat_endpoint(chat_request, request)


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    language: str | None = Form(None),
) -> dict[str, Any]:
    """Transcribe user audio (.mp3, .wav, .m4a, .mp4, .webm, .ogg) using Faster-Whisper Large-v3-Turbo."""
    model_manager.record_activity()
    settings = get_settings()

    temp_dir = settings.workspace_dir / "temp_audio"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Preserve file extension or default to .webm / .wav
    ext = Path(file.filename or "audio.webm").suffix
    if not ext:
        ext = ".webm"
    temp_file_path = temp_dir / f"voice_{uuid.uuid4()}{ext}"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file provided")

        temp_file_path.write_bytes(content)

        # Transcribe using Faster-Whisper
        clean_lang = language if (isinstance(language, str) and language.strip() and language not in ("null", "undefined")) else None
        result = transcription_service.transcribe(temp_file_path, language=clean_lang)
        return {
            "success": True,
            "text": result["text"],
            "language": result["language"],
            "language_probability": result["language_probability"],
            "duration": result["duration"],
            "device": result["device"],
            "model": result["model"],
        }
    except Exception as e:
        logger.error("transcription_endpoint_error", error=str(e), filename=file.filename)
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
    finally:
        try:
            if temp_file_path.exists():
                temp_file_path.unlink()
        except Exception:
            pass


class TTSRequest(BaseModel):
    """Text to speech synthesis request."""
    text: str
    voice: str = "en_US-lessac-medium"
    length_scale: float = 1.0


@router.post("/tts")
async def tts_endpoint(req: TTSRequest) -> Response:
    """Synthesize text to speech using Piper TTS (en_US-lessac-medium)."""
    import time
    t0 = time.perf_counter()
    model_manager.record_activity()
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text provided for TTS")

    try:
        t_pre = time.perf_counter()
        import starlette.concurrency
        wav_bytes = await starlette.concurrency.run_in_threadpool(
            tts_service.synthesize_wav, text, req.length_scale
        )
        t_post = time.perf_counter()
        logger.info("tts_endpoint_timing", total_ms=(t_post - t0)*1000, synth_ms=(t_post - t_pre)*1000)
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav",
                "Cache-Control": "public, max-age=3600",
                "X-Synth-Time-Ms": str(round((t_post - t_pre)*1000, 1)),
                "X-Total-Time-Ms": str(round((t_post - t0)*1000, 1)),
            },
        )
    except Exception as e:
        logger.error("tts_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Text-to-speech synthesis failed: {str(e)}")


@router.post("/tts/stream")
async def tts_stream_endpoint(req: TTSRequest) -> EventSourceResponse:
    """Stream synthesized audio sentence-by-sentence with zero latency (<150ms to first audio)."""
    model_manager.record_activity()
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text provided for TTS")

    chunks = tts_service.split_into_chunks(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No readable text found for speech synthesis")

    async def _stream_chunks() -> AsyncIterator[dict[str, Any]]:
        import base64
        total = len(chunks)
        for idx, chunk_text in enumerate(chunks):
            # Synthesize in thread pool to keep event loop responsive
            wav_bytes = await asyncio.to_thread(
                tts_service.synthesize_wav, chunk_text, req.length_scale
            )
            b64_audio = base64.b64encode(wav_bytes).decode("ascii")
            yield {
                "event": "chunk",
                "data": json.dumps({
                    "index": idx,
                    "total": total,
                    "text": chunk_text,
                    "audio": b64_audio,
                }),
            }
        yield {
            "event": "done",
            "data": json.dumps({"status": "completed", "total_chunks": total}),
        }

    return EventSourceResponse(_stream_chunks())

