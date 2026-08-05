"""Tests for the CNS inbox Speaker."""

import json
import pytest
from pathlib import Path

from wesley_cns.speaker import Speaker


class TestSpeaker:
    def test_speak_creates_file(self, tmp_path):
        speaker = Speaker(tmp_path)
        path = speaker.speak("Hello, world!")
        assert path.exists()
        assert path.suffix == ".json"

    def test_speak_writes_valid_json(self, tmp_path):
        speaker = Speaker(tmp_path)
        path = speaker.speak("Test message")
        data = json.loads(path.read_text())
        assert "header" in data
        assert "body" in data

    def test_speak_contains_response_text(self, tmp_path):
        speaker = Speaker(tmp_path)
        path = speaker.speak("My response text")
        data = json.loads(path.read_text())
        assert data["body"]["payload"]["data"]["response"] == "My response text"

    def test_speak_increments_filename(self, tmp_path):
        """Each call should produce a unique filename."""
        speaker = Speaker(tmp_path)
        p1 = speaker.speak("first")
        p2 = speaker.speak("second")
        assert p1.name != p2.name

    def test_speak_creates_inbox_if_missing(self, tmp_path):
        inbox = tmp_path / "deep" / "nested" / "inbox"
        speaker = Speaker(inbox)
        path = speaker.speak("Hi")
        assert inbox.is_dir()
        assert path.exists()

    def test_speak_custom_agent_id(self, tmp_path):
        speaker = Speaker(tmp_path, agent_id="riker")
        path = speaker.speak("message")
        data = json.loads(path.read_text())
        assert data["header"]["origin_id"] == "riker"

    def test_speak_filename_starts_with_agent(self, tmp_path):
        speaker = Speaker(tmp_path, agent_id="wesley")
        path = speaker.speak("hi")
        assert path.name.startswith("wesley_")

    def test_speak_preserves_intent_mapping(self, tmp_path):
        speaker = Speaker(tmp_path)
        path = speaker.speak("halt!", original_intent="EMERGENCY_HALT")
        data = json.loads(path.read_text())
        assert data["body"]["intent"] == "EMERGENCY_ACK"
        assert data["header"]["priority"] == "CRITICAL"

    def test_atomic_write_no_temp_left(self, tmp_path):
        speaker = Speaker(tmp_path)
        speaker.speak("clean")
        # No .tmp files should remain
        temps = list(tmp_path.glob(".*.tmp"))
        assert temps == []
