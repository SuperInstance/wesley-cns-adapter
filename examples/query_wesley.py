"""Example: Query Wesley (via Ollama) with a CNS signal and get a response.

Requires Ollama running locally with a Granite model pulled.

Run:
    python examples/query_wesley.py
"""

import json
from pathlib import Path

import requests

from wesley_cns.listener import Listener
from wesley_cns.speaker import Speaker
from wesley_cns.translator import build_ollama_request, uscp_to_messages

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "granite3-dense:2b"

INBOX = Path.home() / ".hermes" / "cns_inbox"
OUTBOX = Path.home() / ".hermes" / "cns_outbox"


def query_ollama(messages: list[dict]) -> str:
    body = build_ollama_request(messages, model=MODEL, temperature=0.7)
    try:
        resp = requests.post(OLLAMA_URL, json=body, timeout=60)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"[Error: {e}]"


def main():
    listener = Listener(OUTBOX, agent_id="wesley")
    speaker = Speaker(INBOX, agent_id="wesley")

    signals = listener.scan()
    if not signals:
        # Demo: create a fake signal
        print("No real signals — creating a demo query.")
        demo_packet = {
            "header": {
                "origin_id": "lucineer-riker",
                "timestamp": "2026-08-05T00:00:00Z",
                "priority": "NORMAL",
                "sequence_id": 99,
            },
            "body": {
                "intent": "QUERY",
                "payload": {
                    "type": "signal",
                    "data": {"question": "What's your status, Wesley?"},
                },
            },
        }
        signals = [(Path("/tmp/demo"), demo_packet)]

    for filepath, packet in signals:
        origin = packet.get("header", {}).get("origin_id", "?")
        intent = packet.get("body", {}).get("intent", "?")
        print(f"\n  ◆ [{origin}] {intent}")

        messages = uscp_to_messages(packet)
        print(f"  → Querying {MODEL}...")
        response_text = query_ollama(messages)
        print(f"  ← {response_text[:200]}")

        path = speaker.speak(
            wesley_text=response_text,
            target_id=origin,
            original_intent=intent,
            model=MODEL,
        )
        print(f"  ✓ Sent: {path.name}")


if __name__ == "__main__":
    main()
