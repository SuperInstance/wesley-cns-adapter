"""Translates USCP packets to and from Ollama chat prompts.

Wesley runs on Granite (IBM) via Ollama. This translator:
- Converts incoming USCP signals into natural-language chat messages
- Converts Wesley's text responses back into USCP-v1 response packets
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional


WESLEY_SYSTEM_PROMPT = """\
You are Wesley, an AI agent connected to the CNS (Central Nervous System) signal bus.
You receive structured signals from other agents in the ecosystem.

When you receive a signal, respond naturally and concisely.
If the signal requires action, indicate what you can do.
If it's informational, acknowledge it briefly.
If it's an emergency, prioritize urgency in your response.

You are part of a multi-agent system. Be helpful, direct, and aware of your role as a node in the network.
"""


@dataclass
class OllamaMessage:
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


def uscp_to_messages(packet: dict) -> list[dict]:
    """Convert a USCP packet into an Ollama chat message sequence.

    Returns a list of messages suitable for Ollama's /api/chat endpoint:
    [{"role": "system", ...}, {"role": "user", ...}]
    """
    header = packet.get("header", {})
    body = packet.get("body", {})
    payload = body.get("payload", {})

    origin = header.get("origin_id", "unknown")
    intent = body.get("intent", "UNKNOWN")
    priority = header.get("priority", "MEDIUM")
    timestamp = header.get("timestamp", "?")
    seq = header.get("sequence_id", "?")

    # Build a natural-language representation of the signal
    parts = [
        f"[CNS SIGNAL from {origin}]",
        f"Intent: {intent}",
        f"Priority: {priority}",
        f"Timestamp: {timestamp}",
        f"Sequence: {seq}",
    ]

    payload_data = payload.get("data", payload)
    if payload_data:
        if isinstance(payload_data, (dict, list)):
            parts.append(f"Payload: {json.dumps(payload_data, indent=2)}")
        else:
            parts.append(f"Payload: {payload_data}")

    user_msg = "\n".join(parts)

    return [
        OllamaMessage("system", WESLEY_SYSTEM_PROMPT).to_dict(),
        OllamaMessage("user", user_msg).to_dict(),
    ]


def response_to_uscp(
    wesley_text: str,
    target_id: str,
    original_intent: str = "",
    original_priority: str = "MEDIUM",
    agent_id: str = "wesley",
    model: str = "granite",
) -> dict:
    """Convert Wesley's text response into a USCP-v1 response packet."""
    from datetime import datetime, timezone

    # Determine response intent based on original
    if original_intent == "EMERGENCY_HALT":
        resp_intent = "EMERGENCY_ACK"
        resp_priority = "CRITICAL"
    elif original_intent in ("INTRODUCTION", "HANDSHAKE_COMPLETE"):
        resp_intent = "HANDSHAKE_COMPLETE"
        resp_priority = "HIGH"
    elif original_intent == "REQUEST_REASONING":
        resp_intent = "REASONING_RESPONSE"
        resp_priority = original_priority
    elif original_intent == "QUERY":
        resp_intent = "QUERY_RESPONSE"
        resp_priority = original_priority
    else:
        resp_intent = "WESLEY_RESPONSE"
        resp_priority = original_priority

    return {
        "header": {
            "origin_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": resp_priority,
            "sequence_id": 1,
        },
        "body": {
            "intent": resp_intent,
            "payload": {
                "type": "agent_response",
                "data": {
                    "agent": agent_id,
                    "model": model,
                    "response": wesley_text,
                    "in_response_to": original_intent,
                    "addressed_to": target_id,
                },
            },
        },
        "signature": {
            "type": "USCP-v1",
            "checksum": "verified",
        },
    }


def build_ollama_request(
    messages: list[dict],
    model: str = "granite3-dense:8b",
    stream: bool = False,
    temperature: float = 0.7,
) -> dict:
    """Build the request body for Ollama's /api/chat endpoint."""
    return {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
        },
    }
