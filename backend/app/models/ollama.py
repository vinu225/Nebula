"""
Sovereign AI Workbench — Ollama Model Provider

Implements the ModelProvider interface for Ollama.
Uses langchain-ollama for LangChain-compatible integration
and httpx for direct Ollama API calls (health, model listing).
"""

from __future__ import annotations

import base64
import json
from typing import Any, AsyncIterator

import httpx
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.base import GenerationResult, ModelProvider

logger = get_logger(__name__)


class OllamaProvider(ModelProvider):
    """Model provider backed by a local Ollama server.

    Supports text generation, streaming, and vision (multimodal) inputs.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.ollama_timeout
        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        self._chat_models: dict[str, ChatOllama] = {}

    def _get_chat_model(self, model_name: str, **kwargs: Any) -> ChatOllama:
        """Get or create a ChatOllama instance for a model.

        Instances are cached to avoid re-initialization overhead.
        """
        req_timeout = kwargs.pop("timeout", self.timeout)
        cache_key = f"{model_name}:{req_timeout}:{hash(frozenset(kwargs.items()))}"
        if cache_key not in self._chat_models:
            self._chat_models[cache_key] = ChatOllama(
                model=model_name,
                base_url=self.base_url,
                timeout=req_timeout,
                **kwargs,
            )
        return self._chat_models[cache_key]

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[HumanMessage | SystemMessage | AIMessage]:
        """Convert OpenAI-format messages to LangChain message objects.

        Handles text-only and multimodal (image) messages.
        """
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle multimodal content (list of content blocks)
            if isinstance(content, list):
                parts = []
                for block in content:
                    if block.get("type") == "text":
                        parts.append({"type": "text", "text": block["text"]})
                    elif block.get("type") == "image_url":
                        image_url = block["image_url"]["url"]
                        parts.append({
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        })
                    elif block.get("type") == "image_base64":
                        b64_data = block["data"]
                        media_type = block.get("media_type", "image/png")
                        parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64_data}"
                            },
                        })
                content = parts

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        return lc_messages

    async def resolve_model_name(self, model_name: str) -> str:
        """Resolve model name to an actually installed model in Ollama.

        Handles tag mismatches like 'qwen2.5-coder:8b' -> 'qwen2.5-coder:latest'.
        """
        try:
            available = await self.list_available_models()
            if not available:
                return model_name
            if model_name in available:
                return model_name
            prefix = model_name.split(":")[0]
            for m in available:
                if m == prefix or m.startswith(f"{prefix}:"):
                    return m
            for m in available:
                if prefix in m:
                    return m
        except Exception:
            pass
        return model_name

    async def generate(
        self,
        model_name: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a complete response from an Ollama model.

        Args:
            model_name: Ollama model name (e.g., 'qwen3:8b').
            messages: Chat messages in OpenAI-compatible format.
            **kwargs: Additional parameters (temperature, etc.).

        Returns:
            GenerationResult with the model's response.
        """
        model_name = await self.resolve_model_name(model_name)
        logger.info("ollama_generate_start", model=model_name)
        # Vision models need longer timeout due to image processing on limited VRAM
        effective_timeout = 300 if "vl" in model_name.lower() else self.timeout

        # Use direct httpx /api/chat to avoid LangChain's strict message validation
        # which raises "model output must contain either output text or tool calls"
        # when Ollama produces thinking-only or momentarily empty content chunks.
        try:
            return await self._generate_direct(model_name, messages, effective_timeout, **kwargs)
        except Exception as direct_err:
            logger.warning("ollama_direct_generate_failed", model=model_name, error=str(direct_err))

        # Fallback: LangChain ChatOllama path
        chat_model = self._get_chat_model(model_name, timeout=effective_timeout, **kwargs)
        lc_messages = self._convert_messages(messages)
        try:
            response = await chat_model.ainvoke(lc_messages)
            content = response.content if isinstance(response.content, str) else str(response.content)
            if not content:
                content = "I have analyzed your request. Please let me know if you need any clarification."
            result = GenerationResult(
                content=content,
                model=model_name,
                finish_reason="stop",
                usage=response.response_metadata.get("usage", None) if hasattr(response, "response_metadata") else None,
            )
            logger.info("ollama_generate_complete", model=model_name, content_length=len(content))
            return result
        except Exception as e:
            error_msg = str(e)
            # LangGraph/LangChain raises this when message content is empty
            if "model output" in error_msg or "output text" in error_msg or "tool calls" in error_msg:
                logger.warning("ollama_empty_output_recovered", model=model_name)
                return GenerationResult(
                    content="I have processed your request. The model returned an empty response — this can occur with reasoning models. Please try rephrasing or ask a follow-up question.",
                    model=model_name,
                    finish_reason="empty",
                )
            logger.error("ollama_generate_error", model=model_name, error=error_msg)
            raise

    async def _generate_direct(
        self,
        model_name: str,
        messages: list[dict[str, Any]],
        timeout: int,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate response using direct httpx call to Ollama /api/chat.

        Bypasses LangChain validation that rejects empty or thinking-only outputs.
        Collects both thinking and content from all chunks into a final response.
        """
        payload = {
            "model": model_name,
            "messages": self._to_ollama_messages(messages),
            "stream": False,
        }
        if kwargs:
            payload["options"] = kwargs

        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
            response = await client.post("/api/chat", json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
            data = response.json()
            msg = data.get("message", {})
            content = msg.get("content", "") or ""
            thinking = msg.get("thinking", "") or ""
            # If model only produced thinking with no answer, use thinking as content
            if not content.strip() and thinking.strip():
                content = thinking.strip()
            if not content.strip():
                content = "I have processed your request. Please ask a follow-up if needed."
            logger.info("ollama_direct_generate_complete", model=model_name, content_length=len(content))
            return GenerationResult(
                content=content,
                model=model_name,
                finish_reason=data.get("done_reason", "stop"),
            )

    def _to_ollama_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert standard message format to Ollama native chat format."""
        ollama_msgs = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            images = []
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "image_base64":
                        images.append(block.get("data", ""))
                    elif block.get("type") == "image_url":
                        url = block.get("image_url", {}).get("url", "")
                        if "," in url:
                            images.append(url.split(",", 1)[1])
                        else:
                            images.append(url)
                content_str = "\n".join(text_parts)
                entry = {"role": role, "content": content_str}
                if images:
                    entry["images"] = images
                ollama_msgs.append(entry)
            else:
                ollama_msgs.append({"role": role, "content": str(content)})
        return ollama_msgs

    async def stream(
        self,
        model_name: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream response tokens from an Ollama model, including native reasoning/thinking.

        Args:
            model_name: Ollama model name.
            messages: Chat messages in OpenAI-compatible format.
            **kwargs: Additional parameters.

        Yields:
            Individual tokens as strings. Encloses reasoning chunks in <think>...</think>.
        """
        model_name = await self.resolve_model_name(model_name)
        logger.info("ollama_stream_start", model=model_name)
        effective_timeout = 300 if "vl" in model_name.lower() else self.timeout

        payload = {
            "model": model_name,
            "messages": self._to_ollama_messages(messages),
            "stream": True,
        }
        if kwargs:
            payload["options"] = kwargs

        in_think = False
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=effective_timeout) as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        raise RuntimeError(f"Ollama error {response.status_code}: {err_body.decode()}")

                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        try:
                            chunk_data = json.loads(line)
                        except Exception:
                            continue

                        msg = chunk_data.get("message", {})
                        thinking_chunk = msg.get("thinking")
                        content_chunk = msg.get("content")

                        if thinking_chunk:
                            if not in_think:
                                yield "<think>"
                                in_think = True
                            yield thinking_chunk

                        if content_chunk:
                            if in_think:
                                yield "</think>"
                                in_think = False
                            yield content_chunk

                    if in_think:
                        yield "</think>"
        except Exception as e:
            logger.error("ollama_stream_error", model=model_name, error=str(e))
            # Fallback to chat_model.astream if native endpoint fails
            try:
                chat_model = self._get_chat_model(model_name, timeout=effective_timeout, **kwargs)
                lc_messages = self._convert_messages(messages)
                async for chunk in chat_model.astream(lc_messages):
                    if chunk.content:
                        yield chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            except Exception:
                raise e

    async def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available in Ollama.

        Args:
            model_name: Model name to check.

        Returns:
            True if the model is pulled and available.
        """
        try:
            response = await self._http_client.get("/api/tags")
            if response.status_code != 200:
                return False
            data = response.json()
            available_models = [m["name"] for m in data.get("models", [])]
            # Check exact match or match without tag
            return (
                model_name in available_models
                or any(m.startswith(model_name.split(":")[0]) for m in available_models)
            )
        except Exception as e:
            logger.warning("ollama_model_check_failed", model=model_name, error=str(e))
            return False

    async def list_available_models(self) -> list[str]:
        """List all models available in Ollama.

        Returns:
            List of model name strings.
        """
        try:
            response = await self._http_client.get("/api/tags")
            if response.status_code != 200:
                return []
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def get_loaded_models(self) -> list[dict[str, Any]]:
        """List all models currently running / loaded in Ollama memory."""
        try:
            response = await self._http_client.get("/api/ps")
            if response.status_code == 200:
                return response.json().get("models", [])
            return []
        except Exception as e:
            logger.warning("ollama_get_loaded_models_failed", error=str(e))
            return []

    async def unload_model(self, model_name: str) -> bool:
        """Unload a specific model from Ollama memory (GPU VRAM / RAM).

        Calls /api/generate with keep_alive=0 to immediately free resources.
        """
        try:
            response = await self._http_client.post(
                "/api/generate",
                json={"model": model_name, "keep_alive": 0},
                timeout=15,
            )
            if response.status_code == 200:
                logger.info("ollama_model_unloaded", model=model_name)
                return True
            logger.warning("ollama_unload_status_code", model=model_name, status=response.status_code)
            return False
        except Exception as e:
            logger.warning("ollama_unload_model_failed", model=model_name, error=str(e))
            return False

    async def unload_all_models(self) -> list[str]:
        """Unload all currently running models from memory to free VRAM/RAM.

        Returns:
            List of model names that were unloaded.
        """
        loaded = await self.get_loaded_models()
        stopped: list[str] = []
        for m in loaded:
            m_name = m.get("name") or m.get("model")
            if m_name:
                ok = await self.unload_model(m_name)
                if ok:
                    stopped.append(m_name)

        # In case /api/ps didn't catch something or as a safety sweep:
        # also try common configured models if any is still loaded
        common_models = ["qwen3:8b", "qwen3.5:4b", "qwen3-vl:8b", "qwen2.5-coder:latest"]
        for m_name in common_models:
            if m_name not in stopped:
                try:
                    await self.unload_model(m_name)
                except Exception:
                    pass

        return stopped

    async def health_check(self) -> bool:
        """Check if the Ollama server is healthy.

        Returns:
            True if Ollama is reachable.
        """
        try:
            response = await self._http_client.get("/")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Clean up HTTP client resources."""
        await self._http_client.aclose()
