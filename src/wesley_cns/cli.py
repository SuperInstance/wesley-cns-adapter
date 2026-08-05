"""CLI entry point for wesley-cns."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

from . import __version__
from .listener import Listener
from .speaker import Speaker
from .translator import build_ollama_request, uscp_to_messages


def default_inbox() -> str:
    return os.path.expanduser("~/.hermes/cns_inbox/")


def default_outbox() -> str:
    return os.path.expanduser("~/.hermes/cns_outbox/")


def call_ollama(
    messages: list[dict],
    model: str,
    host: str = "localhost",
    port: int = 11434,
    timeout: float = 60.0,
) -> str:
    """Call Ollama's /api/chat endpoint and return the response text."""
    url = f"http://{host}:{port}/api/chat"
    body = build_ollama_request(messages, model=model)

    try:
        resp = requests.post(url, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        return "[Wesley offline — Ollama not reachable]"
    except requests.exceptions.Timeout:
        return "[Wesley timeout — Ollama took too long]"
    except Exception as e:
        return f"[Wesley error — {e}]"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wesley-cns",
        description="Connects Wesley (Granite via Ollama) to the CNS signal bus.",
    )
    parser.add_argument(
        "--inbox",
        default=default_inbox(),
        help="Path to cns_inbox for sending responses (default: ~/.hermes/cns_inbox/)",
    )
    parser.add_argument(
        "--outbox",
        default=default_outbox(),
        help="Path to cns_outbox to listen on (default: ~/.hermes/cns_outbox/)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously watch for incoming signals and respond",
    )
    parser.add_argument(
        "--model",
        default="granite3-dense:8b",
        help="Ollama model to use (default: granite3-dense:8b)",
    )
    parser.add_argument(
        "--ollama-host",
        default="localhost",
        help="Ollama API host (default: localhost)",
    )
    parser.add_argument(
        "--ollama-port",
        type=int,
        default=11434,
        help="Ollama API port (default: 11434)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Poll interval in seconds when --watch (default: 1.0)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Ollama temperature (default: 0.7)",
    )
    parser.add_argument(
        "--agent-id",
        default="wesley",
        help="Agent identifier in USCP packets (default: wesley)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process signals and print Wesley's response without sending",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"wesley-cns {__version__}",
    )

    args = parser.parse_args()

    inbox = Path(args.inbox)
    outbox = Path(args.outbox)

    listener = Listener(outbox, agent_id=args.agent_id, poll_interval=args.interval)
    speaker = Speaker(inbox, agent_id=args.agent_id)

    def process_signal(filepath: Path, packet: dict) -> None:
        header = packet.get("header", {})
        body = packet.get("body", {})

        origin = header.get("origin_id", "?")
        intent = body.get("intent", "?")
        priority = header.get("priority", "?")

        print(f"\n  ◆ INBOUND [{priority}] from {origin}: {intent}")

        # Translate to Ollama messages
        messages = uscp_to_messages(packet)

        # Override temperature if specified
        print(f"  → Querying Wesley ({args.model})...")

        # Build request with custom temperature
        request_body = build_ollama_request(
            messages,
            model=args.model,
            temperature=args.temperature,
        )

        # Call Ollama
        url = f"http://{args.ollama_host}:{args.ollama_port}/api/chat"

        try:
            resp = requests.post(url, json=request_body, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            wesley_text = data.get("message", {}).get("content", "").strip()
        except requests.exceptions.ConnectionError:
            wesley_text = "[Wesley offline — Ollama not reachable]"
            print(f"  ⚠ Ollama not reachable at {args.ollama_host}:{args.ollama_port}", file=sys.stderr)
        except requests.exceptions.Timeout:
            wesley_text = "[Wesley timeout — Ollama took too long]"
            print(f"  ⚠ Ollama timeout", file=sys.stderr)
        except Exception as e:
            wesley_text = f"[Wesley error — {e}]"
            print(f"  ⚠ Ollama error: {e}", file=sys.stderr)

        print(f"  ← Wesley: {wesley_text[:200]}")

        if not args.dry_run:
            response_path = speaker.speak(
                wesley_text=wesley_text,
                target_id=origin,
                original_intent=intent,
                original_priority=priority,
            )
            print(f"  ✓ Response sent: {response_path.name}")
        else:
            print(f"  (dry-run — response not sent)")

    if args.watch:
        print(f"wesley-cns v{__version__} — listening on {outbox}")
        print(f"  Agent: {args.agent_id}")
        print(f"  Model: {args.model}")
        print(f"  Ollama: {args.ollama_host}:{args.ollama_port}")
        print(f"  Inbox: {inbox}")
        print(f"  Poll: {args.interval}s")
        print()

        listener.watch(process_signal)
    else:
        # One-shot: process current unread signals
        signals = listener.scan()
        if not signals:
            print("No unread signals for Wesley.")
            sys.exit(0)

        print(f"wesley-cns v{__version__} — processing {len(signals)} signal(s)")
        for filepath, packet in signals:
            process_signal(filepath, packet)


if __name__ == "__main__":
    main()
