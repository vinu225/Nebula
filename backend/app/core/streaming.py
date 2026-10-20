import json
import asyncio
from typing import AsyncGenerator, Optional, Tuple

async def parse_thinking_stream(token_stream: AsyncGenerator[str, None], model_name: str = "") -> AsyncGenerator[dict, None]:
    """
    Parses a stream of text chunks from an LLM that may contain <think>...</think> tags.
    Yields SSE-compatible event dictionaries:
      - {"event": "thinking_start", "data": ...}
      - {"event": "thinking", "data": ...}
      - {"event": "thinking_done", "data": ...}
      - {"event": "token", "data": ...}
    """
    yield {
        "event": "thinking_start",
        "data": json.dumps({"model": model_name or "sovereign-agent"}),
    }

    buffer = ""
    in_think = False
    has_thought = False

    async for chunk in token_stream:
        buffer += chunk

        while buffer:
            if not in_think:
                ts = buffer.find("<think>")
                if ts != -1:
                    before = buffer[:ts]
                    if before:
                        yield {"event": "token", "data": json.dumps({"token": before})}
                    in_think = True
                    has_thought = True
                    buffer = buffer[ts + len("<think>"):]
                else:
                    # Check for partial prefix of "<think>" at the end
                    matched_prefix_len = 0
                    for pl in range(min(len(buffer), len("<think>") - 1), 0, -1):
                        if "<think>".startswith(buffer[-pl:]):
                            matched_prefix_len = pl
                            break

                    if matched_prefix_len > 0:
                        emit_part = buffer[:-matched_prefix_len]
                        buffer = buffer[-matched_prefix_len:]
                        if emit_part:
                            yield {"event": "token", "data": json.dumps({"token": emit_part})}
                        break
                    else:
                        yield {"event": "token", "data": json.dumps({"token": buffer})}
                        buffer = ""
            else:
                te = buffer.find("</think>")
                if te != -1:
                    think_part = buffer[:te]
                    if think_part:
                        yield {"event": "thinking", "data": json.dumps({"token": think_part})}
                    yield {"event": "thinking_done", "data": json.dumps({})}
                    in_think = False
                    buffer = buffer[te + len("</think>"):].lstrip("\r\n")
                else:
                    matched_prefix_len = 0
                    for pl in range(min(len(buffer), len("</think>") - 1), 0, -1):
                        if "</think>".startswith(buffer[-pl:]):
                            matched_prefix_len = pl
                            break

                    if matched_prefix_len > 0:
                        emit_part = buffer[:-matched_prefix_len]
                        buffer = buffer[-matched_prefix_len:]
                        if emit_part:
                            yield {"event": "thinking", "data": json.dumps({"token": emit_part})}
                        break
                    else:
                        yield {"event": "thinking", "data": json.dumps({"token": buffer})}
                        buffer = ""

    # Flush remaining buffer if any
    if buffer:
        if in_think:
            yield {"event": "thinking", "data": json.dumps({"token": buffer})}
            yield {"event": "thinking_done", "data": json.dumps({})}
        else:
            yield {"event": "token", "data": json.dumps({"token": buffer})}

    if in_think:
        yield {"event": "thinking_done", "data": json.dumps({})}


async def forward_stream_with_thinking(
    token_stream: AsyncGenerator[str, None],
    stream_queue: asyncio.Queue,
    model_name: str = "",
    initial_answer_prefix: str = "",
) -> Tuple[str, str]:
    """
    Consumes token_stream, emits thinking and answer events to stream_queue,
    and returns (full_thinking_text, full_answer_text).
    Emits initial_answer_prefix right when answer tokens start, so headers don't precede thinking.
    """
    thinking_chunks = []
    answer_chunks = []
    prefix_emitted = False

    async for event_dict in parse_thinking_stream(token_stream, model_name=model_name):
        evt = event_dict.get("event")
        data = json.loads(event_dict.get("data", "{}"))

        if evt == "thinking" and "token" in data:
            thinking_chunks.append(data["token"])
            await stream_queue.put(event_dict)
        elif evt == "token" and "token" in data:
            if not prefix_emitted and initial_answer_prefix:
                await stream_queue.put({"event": "token", "data": json.dumps({"token": initial_answer_prefix})})
                answer_chunks.append(initial_answer_prefix)
                prefix_emitted = True
            await stream_queue.put(event_dict)
            answer_chunks.append(data["token"])
        else:
            await stream_queue.put(event_dict)

    if not prefix_emitted and initial_answer_prefix and answer_chunks:
        answer_chunks.insert(0, initial_answer_prefix)

    return "".join(thinking_chunks), "".join(answer_chunks)
