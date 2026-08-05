"""Sends Wesley's responses through the CNS inbox."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .translator import response_to_uscp


class Speaker:
    """Writes Wesley's response packets into the CNS inbox."""

    def __init__(
        self,
        inbox_path: str | Path,
        agent_id: str = "wesley",
    ) -> None:
        self.inbox = Path(inbox_path)
        self.agent_id = agent_id

    def speak(
        self,
        wesley_text: str,
        target_id: str = "hermes-cns",
        original_intent: str = "",
        original_priority: str = "MEDIUM",
    ) -> Path:
        """Write Wesley's response as a USCP packet to the inbox."""
        self.inbox.mkdir(parents=True, exist_ok=True)

        packet = response_to_uscp(
            wesley_text=wesley_text,
            target_id=target_id,
            original_intent=original_intent,
            original_priority=original_priority,
            agent_id=self.agent_id,
        )

        timestamp_str = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"{self.agent_id}_{timestamp_str}_001.json"

        # Atomic write: temp then rename
        tmp_path = self.inbox / f".{filename}.tmp"
        final_path = self.inbox / filename

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(packet, f, indent=2)

        os.rename(str(tmp_path), str(final_path))
        return final_path
