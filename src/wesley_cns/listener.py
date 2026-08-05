"""Polls cns_outbox for USCP signals addressed to Wesley."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Optional


class Listener:
    """Watches the CNS outbox for signals addressed to Wesley.

    Wesley listens on the outbox because from an agent's perspective,
    incoming messages from Hermes arrive in the outbox.
    """

    def __init__(
        self,
        outbox_path: str | Path,
        agent_id: str = "wesley",
        poll_interval: float = 1.0,
    ) -> None:
        self.outbox = Path(outbox_path)
        self.agent_id = agent_id
        self.poll_interval = poll_interval
        self._seen: set[str] = set()

    def _is_for_wesley(self, packet: dict) -> bool:
        """Check if a packet is addressed to Wesley.

        We check several conventions:
        1. Filename contains 'wesley'
        2. Payload data has 'addressed_to': 'wesley'
        3. Packet targets our agent_id in any standard field
        4. If no specific target, accept all (broadcast mode)
        """
        # Check payload for explicit addressing
        payload = packet.get("body", {}).get("payload", {})
        data = payload.get("data", {})

        if isinstance(data, dict):
            addressed_to = data.get("addressed_to", "").lower()
            if addressed_to:
                return self.agent_id.lower() in addressed_to or addressed_to == "all"

        return True  # Broadcast: accept signals without explicit addressing

    def scan(self) -> list[tuple[Path, dict]]:
        """Scan outbox for unprocessed signals. Returns (filepath, packet) pairs."""
        results: list[tuple[Path, dict]] = []

        if not self.outbox.is_dir():
            return results

        for entry in sorted(self.outbox.iterdir()):
            if not entry.is_file() or entry.suffix != ".json":
                continue
            if entry.name in self._seen:
                continue
            if entry.name.startswith("."):
                continue

            try:
                with open(entry, "r", encoding="utf-8") as f:
                    packet = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            if self._is_for_wesley(packet):
                self._seen.add(entry.name)
                results.append((entry, packet))

        return results

    def watch(self, callback: Callable[[Path, dict], None]) -> None:
        """Block forever, polling for new signals and calling the callback."""
        while True:
            for filepath, packet in self.scan():
                callback(filepath, packet)
            time.sleep(self.poll_interval)
