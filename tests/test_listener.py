"""Tests for the CNS outbox Listener."""

import json
import pytest
from pathlib import Path

from wesley_cns.listener import Listener


def write_packet(directory: Path, name: str, packet: dict) -> Path:
    """Write a JSON packet to a directory."""
    p = directory / name
    p.write_text(json.dumps(packet))
    return p


def make_packet(origin="hermes-cns", addressed_to="wesley", intent="QUERY"):
    data = {"addressed_to": addressed_to} if addressed_to else {}
    return {
        "header": {
            "origin_id": origin,
            "timestamp": "2026-08-05T07:00:00Z",
            "priority": "MEDIUM",
            "sequence_id": 1,
        },
        "body": {
            "intent": intent,
            "payload": {"type": "signal", "data": data},
        },
    }


class TestListenerScan:
    def test_empty_directory(self, tmp_path):
        listener = Listener(tmp_path)
        assert listener.scan() == []

    def test_finds_json_packet(self, tmp_path):
        pkt = make_packet()
        write_packet(tmp_path, "hermes_001.json", pkt)
        listener = Listener(tmp_path)
        results = listener.scan()
        assert len(results) == 1
        _, found = results[0]
        assert found["header"]["origin_id"] == "hermes-cns"

    def test_ignores_non_json(self, tmp_path):
        write_packet(tmp_path, "readme.txt", {})
        listener = Listener(tmp_path)
        assert listener.scan() == []

    def test_ignores_hidden_files(self, tmp_path):
        write_packet(tmp_path, ".hidden.json", make_packet())
        listener = Listener(tmp_path)
        assert listener.scan() == []

    def test_marks_as_seen(self, tmp_path):
        write_packet(tmp_path, "hermes_001.json", make_packet())
        listener = Listener(tmp_path)
        assert len(listener.scan()) == 1
        # Second scan should not re-find it
        assert len(listener.scan()) == 0

    def test_addressed_to_wesley(self, tmp_path):
        write_packet(tmp_path, "h_001.json", make_packet(addressed_to="wesley"))
        listener = Listener(tmp_path, agent_id="wesley")
        assert len(listener.scan()) == 1

    def test_addressed_to_other(self, tmp_path):
        write_packet(tmp_path, "h_001.json", make_packet(addressed_to="riker"))
        listener = Listener(tmp_path, agent_id="wesley")
        # The listener defaults to broadcast mode, so it accepts everything
        # unless explicitly addressed to someone else
        assert len(listener.scan()) == 0

    def test_broadcast_packet_accepted(self, tmp_path):
        write_packet(tmp_path, "h_001.json", make_packet(addressed_to="all"))
        listener = Listener(tmp_path, agent_id="wesley")
        assert len(listener.scan()) == 1

    def test_invalid_json_skipped(self, tmp_path):
        (tmp_path / "broken.json").write_text("{not valid json")
        listener = Listener(tmp_path)
        assert listener.scan() == []

    def test_missing_directory(self, tmp_path):
        listener = Listener(tmp_path / "nonexistent")
        assert listener.scan() == []

    def test_multiple_packets_sorted(self, tmp_path):
        write_packet(tmp_path, "c_003.json", make_packet())
        write_packet(tmp_path, "a_001.json", make_packet())
        write_packet(tmp_path, "b_002.json", make_packet())
        listener = Listener(tmp_path)
        results = listener.scan()
        names = [p.name for p, _ in results]
        assert names == sorted(names)


class TestListenerWatch:
    def test_callback_invoked(self, tmp_path, monkeypatch):
        """watch() is blocking — test by running one scan cycle manually."""
        write_packet(tmp_path, "h_001.json", make_packet())
        listener = Listener(tmp_path, poll_interval=0.01)

        received = []
        # Manually invoke one scan cycle instead of blocking watch()
        for filepath, packet in listener.scan():
            received.append(packet)
        assert len(received) == 1

    def test_watch_terminates_on_max_iterations(self, tmp_path, monkeypatch):
        """Ensure watch() runs cycles — patch to limit iterations."""
        write_packet(tmp_path, "h_001.json", make_packet())
        listener = Listener(tmp_path, poll_interval=0.01)

        received = []
        call_count = [0]
        original_sleep = listener.__class__.__module__

        # Patch time.sleep to break the watch loop after first call
        import wesley_cns.listener as listener_mod
        original_sleep_fn = listener_mod.time.sleep

        def limited_sleep(seconds):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise KeyboardInterrupt
            original_sleep_fn(seconds)

        monkeypatch.setattr(listener_mod.time, "sleep", limited_sleep)

        with pytest.raises(KeyboardInterrupt):
            listener.watch(lambda fp, pkt: received.append(pkt))
        assert len(received) == 1
