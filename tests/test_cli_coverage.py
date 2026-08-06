"""Coverage gap tests for wesley_cns.cli — targeting the 57% coverage on cli.py.

Missing lines: 125-176 (process_signal + one-shot mode), 179-187 (watch mode setup),
189-197 (dry-run path), 201 (import guard).
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from wesley_cns.cli import call_ollama, default_inbox, default_outbox, main


class TestProcessSignalOneShot:
    """Test the one-shot signal processing path (lines 125-176)."""

    def test_one_shot_with_signal_dry_run(self, tmp_path, capsys):
        """One-shot mode with a signal and --dry-run should print Wesley's response without sending."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {
                "origin_id": "hermes-cns",
                "timestamp": "2026-08-05T12:00:00Z",
                "priority": "HIGH",
                "sequence_id": 1,
            },
            "body": {
                "intent": "QUERY",
                "payload": {"type": "signal", "data": {"message": "hello wesley"}},
            },
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "message": {"content": "Wesley acknowledges the query."}
            }
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
            ]):
                main()  # should NOT raise SystemExit (that only happens when no signals)

        captured = capsys.readouterr()
        assert "INBOUND" in captured.out
        assert "Wesley" in captured.out
        assert "dry-run" in captured.out

    def test_one_shot_with_signal_and_send(self, tmp_path, capsys):
        """One-shot mode with a signal and no --dry-run should write a response to inbox."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {
                "origin_id": "hermes-cns",
                "timestamp": "2026-08-05T12:00:00Z",
                "priority": "HIGH",
                "sequence_id": 1,
            },
            "body": {
                "intent": "HANDSHAKE",
                "payload": {"type": "signal", "data": {"message": "ping"}},
            },
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "message": {"content": "Handshake acknowledged."}
            }
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--model", "granite3.1-dense:2b",
            ]):
                main()

        captured = capsys.readouterr()
        assert "Response sent" in captured.out

        # Check a response file was created in inbox
        response_files = list(inbox.glob("*.json"))
        assert len(response_files) == 1

    def test_one_shot_ollama_offline(self, tmp_path, capsys):
        """One-shot mode when Ollama is unreachable shows offline message."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {
                "origin_id": "hermes-cns",
                "timestamp": "2026-08-05T12:00:00Z",
                "priority": "MEDIUM",
                "sequence_id": 1,
            },
            "body": {
                "intent": "QUERY",
                "payload": {"type": "signal", "data": {"message": "test"}},
            },
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        import requests

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("refused")

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
            ]):
                main()

        captured = capsys.readouterr()
        assert "offline" in captured.out.lower()

    def test_one_shot_ollama_timeout(self, tmp_path, capsys):
        """One-shot mode with Ollama timeout."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {
                "origin_id": "hermes",
                "timestamp": "2026-08-05T12:00:00Z",
                "priority": "LOW",
                "sequence_id": 1,
            },
            "body": {
                "intent": "PING",
                "payload": {"type": "signal", "data": {}},
            },
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        import requests

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("slow")

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
            ]):
                main()

        captured = capsys.readouterr()
        assert "timeout" in captured.out.lower()

    def test_one_shot_ollama_generic_error(self, tmp_path, capsys):
        """One-shot mode with generic Ollama error."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {"origin_id": "test", "timestamp": "2026-08-05T12:00:00Z",
                        "priority": "LOW", "sequence_id": 1},
            "body": {"intent": "TEST", "payload": {"type": "signal", "data": {}}},
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_post.side_effect = RuntimeError("broke")

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
            ]):
                main()

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_one_shot_custom_model_and_host(self, tmp_path, capsys):
        """One-shot mode with custom model and host args."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {"origin_id": "test", "timestamp": "2026-08-05T12:00:00Z",
                        "priority": "MEDIUM", "sequence_id": 1},
            "body": {"intent": "QUERY", "payload": {"type": "signal", "data": {}}},
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"message": {"content": "ok"}}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
                "--model", "custom-model",
                "--ollama-host", "192.168.1.50",
                "--ollama-port", "9999",
                "--temperature", "0.3",
            ]):
                main()

        # Verify the URL contains custom host/port
        call_args = mock_post.call_args
        url = str(call_args[0][0] if call_args[0] else call_args[1].get("url", ""))
        assert "192.168.1.50" in url
        assert "9999" in url

    def test_one_shot_custom_agent_id(self, tmp_path, capsys):
        """One-shot mode with custom agent ID."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        packet = {
            "header": {"origin_id": "test", "timestamp": "2026-08-05T12:00:00Z",
                        "priority": "MEDIUM", "sequence_id": 1},
            "body": {"intent": "QUERY", "payload": {"type": "signal", "data": {}}},
        }
        (outbox / "signal_001.json").write_text(json.dumps(packet))

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"message": {"content": "ok"}}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
                "--agent-id", "custom-wesley",
            ]):
                main()

        captured = capsys.readouterr()
        assert "INBOUND" in captured.out

    def test_one_shot_multiple_signals(self, tmp_path, capsys):
        """One-shot mode with multiple signals processes all of them."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        for i in range(3):
            packet = {
                "header": {"origin_id": "test", "timestamp": f"2026-08-05T12:00:0{i}Z",
                            "priority": "MEDIUM", "sequence_id": i},
                "body": {"intent": "QUERY", "payload": {"type": "signal", "data": {"i": i}}},
            }
            (outbox / f"signal_{i:03d}.json").write_text(json.dumps(packet))

        with patch("wesley_cns.cli.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"message": {"content": "ok"}}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--dry-run",
            ]):
                main()

        captured = capsys.readouterr()
        assert "3 signal(s)" in captured.out


class TestWatchModeStartup:
    """Test watch mode initialization (lines 179-197)."""

    def test_watch_calls_listener_watch(self, tmp_path):
        """Watch mode should call listener.watch()."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        with patch("wesley_cns.cli.Listener") as mock_listener_cls:
            mock_listener = MagicMock()
            mock_listener_cls.return_value = mock_listener

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--watch",
                "--interval", "0.5",
            ]):
                main()

            mock_listener.watch.assert_called_once()

    def test_watch_custom_interval(self, tmp_path):
        """Watch mode passes custom interval to listener."""
        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()
        inbox.mkdir()

        with patch("wesley_cns.cli.Listener") as mock_listener_cls:
            mock_listener = MagicMock()
            mock_listener_cls.return_value = mock_listener

            with patch.object(sys, "argv", [
                "wesley-cns",
                "--outbox", str(outbox),
                "--inbox", str(inbox),
                "--watch",
                "--interval", "2.5",
            ]):
                main()

            # Verify listener was created with poll_interval=2.5
            call_kwargs = mock_listener_cls.call_args[1]
            assert call_kwargs.get("poll_interval") == 2.5


class TestCallOllamaEdgeCases:
    """Additional edge cases for call_ollama."""

    @patch("wesley_cns.cli.requests.post")
    def test_returns_content_with_whitespace(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "  trimmed  "}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        result = call_ollama([], model="m")
        assert result == "trimmed"

    @patch("wesley_cns.cli.requests.post")
    def test_http_error_raises_exception_caught(self, mock_post):
        """HTTP error is caught by generic Exception handler."""
        mock_post.side_effect = ValueError("bad value")
        result = call_ollama([], model="m")
        assert "error" in result.lower()
