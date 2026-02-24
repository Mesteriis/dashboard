from __future__ import annotations

import json

from core.contracts.models import EventEnvelope


def format_sse_event(event: EventEnvelope) -> str:
    payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    return f"id: {event.revision}\nevent: {event.type}\ndata: {payload}\n\n"


__all__ = ["format_sse_event"]
