"""Tests for the wesley-cns CLI module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from wesley_cns.cli import call_ollama, default_inbox, default_outbox, main


class TestCallOllama:
    """Tests for the Ollama API caller."""

    @patch("wesley_cns.cli.requests.post")
    def test_successful_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": "Hello from Wesley!"}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_ollama(
            [{"role": "user", "content": "hi"}],
            model="granite3.1-dense:2b",
        )
        assert result == "Hello from Wesley!"

    @patch("wesley_cns.cli.requests.post")
    def test_empty_content(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "  "}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_ollama([], model="granite3.1-dense:2b")
        assert result == ""

    @patch("wesley_cns.cli.requests.post")
    def test_missing_message_key(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_ollama([], model="granite3.1-dense:2b")
        assert result == ""

    @patch("wesley_cns.cli.requests.post")
    def test_connection_error(self, mock_post):
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        result = call_ollama([], model="granite3.1-dense:2b")
        assert "offline" in result.lower()

    @patch("wesley_cns.cli.requests.post")
    def test_timeout(self, mock_post):
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("slow")
        result = call_ollama([], model="granite3.1-dense:2b")
        assert "timeout" in result.lower()

    @patch("wesley_cns.cli.requests.post")
    def test_generic_error(self, mock_post):
        mock_post.side_effect = RuntimeError("something broke")
        result = call_ollama([], model="granite3.1-dense:2b")
        assert "error" in result.lower()

    @patch("wesley_cns.cli.requests.post")
    def test_custom_host_port(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "ok"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        call_ollama([], model="test", host="192.168.1.100", port=8080)

        call_args = mock_post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert "192.168.1.100" in str(url)
        assert "8080" in str(url)

    @patch("wesley_cns.cli.requests.post")
    def test_timeout_passed_through(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "ok"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        call_ollama([], model="test", timeout=5.0)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == 5.0


class TestDefaultPaths:
    def test_default_inbox_contains_hermes(self):
        path = default_inbox()
        assert "cns_inbox" in path

    def test_default_outbox_contains_hermes(self):
        path = default_outbox()
        assert "cns_outbox" in path

    def test_inbox_expands_home(self):
        path = default_inbox()
        assert "~" not in path  # Should be expanded


class TestCLIMain:
    @patch("sys.argv", ["wesley-cns", "--outbox", "/tmp/test_empty_outbox_cns", "--inbox", "/tmp/test_empty_inbox_cns"])
    def test_no_signals_one_shot(self, tmp_path, capsys):
        """CLI with no signals should print 'No unread signals' and exit."""
        import tempfile
        outbox = Path(tempfile.mkdtemp())
        inbox = Path(tempfile.mkdtemp())

        with patch("sys.argv", ["wesley-cns", "--outbox", str(outbox), "--inbox", str(inbox)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Should exit with code 0
        assert exc_info.value.code == 0

    @patch("sys.argv", ["wesley-cns", "--version"])
    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("sys.argv", ["wesley-cns", "--help"])
    def test_help_flag(self):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


class TestIntegration:
    """Integration tests that use real file I/O."""

    def test_full_pipeline_listener_to_speaker(self, tmp_path):
        """Signal arrives in outbox → listener picks it up → speaker writes response."""
        from wesley_cns.listener import Listener
        from wesley_cns.speaker import Speaker
        from wesley_cns.translator import uscp_to_messages, response_to_uscp

        outbox = tmp_path / "outbox"
        inbox = tmp_path / "inbox"
        outbox.mkdir()

        # Write a signal to the outbox
        packet = {
            "header": {
                "origin_id": "hermes-cns",
                "timestamp": "2026-08-05T12:00:00Z",
                "priority": "HIGH",
                "sequence_id": 1,
            },
            "body": {
                "intent": "HANDSHAKE_COMPLETE",
                "payload": {
                    "type": "signal",
                    "data": {"addressed_to": "wesley", "message": "hello"},
                },
            },
        }
        (outbox / "hermes_001.json").write_text(json.dumps(packet))

        # Listener picks it up
        listener = Listener(outbox, agent_id="wesley")
        signals = listener.scan()
        assert len(signals) == 1

        filepath, found_packet = signals[0]
        assert found_packet["header"]["origin_id"] == "hermes-cns"

        # Translate to messages
        messages = uscp_to_messages(found_packet)
        assert len(messages) == 2

        # Simulate Wesley response
        wesley_text = "Wesley here. Acknowledging handshake."

        # Speaker writes response
        speaker = Speaker(inbox, agent_id="wesley")
        response_path = speaker.speak(
            wesley_text=wesley_text,
            target_id="hermes-cns",
            original_intent="HANDSHAKE_COMPLETE",
        )

        assert response_path.exists()
        response_data = json.loads(response_path.read_text())
        assert response_data["body"]["payload"]["data"]["response"] == wesley_text
        assert response_data["body"]["intent"] == "HANDSHAKE_COMPLETE"

    def test_multiple_signals_processed(self, tmp_path):
        """Multiple signals in the outbox should all be picked up."""
        from wesley_cns.listener import Listener

        outbox = tmp_path / "outbox"
        outbox.mkdir()

        for i in range(5):
            packet = {
                "header": {
                    "origin_id": "hermes-cns",
                    "timestamp": "2026-08-05T12:00:0{}Z".format(i),
                    "priority": "MEDIUM",
                    "sequence_id": i,
                },
                "body": {
                    "intent": "QUERY",
                    "payload": {"type": "signal", "data": {"seq": i}},
                },
            }
            (outbox / f"signal_{i:03d}.json").write_text(json.dumps(packet))

        listener = Listener(outbox)
        results = listener.scan()
        assert len(results) == 5

        # Second scan should find nothing new
        assert len(listener.scan()) == 0

    def test_mixed_valid_invalid_packets(self, tmp_path):
        """Valid and invalid packets in the same outbox."""
        from wesley_cns.listener import Listener

        outbox = tmp_path / "outbox"
        outbox.mkdir()

        # Valid packet
        good = {"header": {"origin_id": "test"}, "body": {"intent": "QUERY"}}
        (outbox / "good.json").write_text(json.dumps(good))

        # Invalid JSON
        (outbox / "bad.json").write_text("{broken")

        # Non-JSON file
        (outbox / "notes.txt").write_text("not a packet")

        # Hidden file
        (outbox / ".hidden.json").write_text(json.dumps(good))

        listener = Listener(outbox)
        results = listener.scan()
        assert len(results) == 1
        assert results[0][0].name == "good.json"
