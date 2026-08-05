"""Tests for the USCP ↔ Ollama translator."""

import pytest
from wesley_cns.translator import (
    OllamaMessage,
    WESLEY_SYSTEM_PROMPT,
    build_ollama_request,
    response_to_uscp,
    uscp_to_messages,
)


# ---- uscp_to_messages ----

def make_packet(
    origin="lucineer-riker",
    intent="REQUEST_REASONING",
    priority="HIGH",
    payload_data=None,
):
    return {
        "header": {
            "origin_id": origin,
            "timestamp": "2026-08-05T07:00:00Z",
            "priority": priority,
            "sequence_id": 42,
        },
        "body": {
            "intent": intent,
            "payload": {
                "type": "agent_signal",
                "data": payload_data or {"question": "status report?"},
            },
        },
    }


class TestUscpToMessages:
    def test_returns_system_and_user_messages(self):
        msgs = uscp_to_messages(make_packet())
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_system_prompt_is_wesley(self):
        msgs = uscp_to_messages(make_packet())
        assert "Wesley" in msgs[0]["content"]

    def test_user_message_contains_origin(self):
        msgs = uscp_to_messages(make_packet(origin="hermes-cns"))
        assert "hermes-cns" in msgs[1]["content"]

    def test_user_message_contains_intent(self):
        msgs = uscp_to_messages(make_packet(intent="HANDSHAKE_COMPLETE"))
        assert "HANDSHAKE_COMPLETE" in msgs[1]["content"]

    def test_user_message_contains_priority(self):
        msgs = uscp_to_messages(make_packet(priority="CRITICAL"))
        assert "CRITICAL" in msgs[1]["content"]

    def test_dict_payload_is_json_formatted(self):
        pkt = make_packet(payload_data={"nested": {"deep": True}})
        msgs = uscp_to_messages(pkt)
        assert '"nested"' in msgs[1]["content"]

    def test_string_payload_is_plain_text(self):
        pkt = make_packet(payload_data="simple text")
        msgs = uscp_to_messages(pkt)
        assert "simple text" in msgs[1]["content"]

    def test_missing_fields_dont_crash(self):
        """Packets missing optional fields should not raise."""
        minimal = {"header": {}, "body": {}}
        msgs = uscp_to_messages(minimal)
        assert len(msgs) == 2

    def test_empty_packet_doesnt_crash(self):
        """Even an empty dict should produce messages."""
        msgs = uscp_to_messages({})
        assert len(msgs) == 2


# ---- response_to_uscp ----

class TestResponseToUscp:
    def test_basic_response_shape(self):
        pkt = response_to_uscp("Hello!", target_id="hermes-cns")
        assert "header" in pkt
        assert "body" in pkt
        assert "signature" in pkt

    def test_origin_is_agent_id(self):
        pkt = response_to_uscp("Hi", target_id="x", agent_id="wesley")
        assert pkt["header"]["origin_id"] == "wesley"

    def test_custom_agent_id(self):
        pkt = response_to_uscp("Hi", target_id="x", agent_id="riker")
        assert pkt["header"]["origin_id"] == "riker"

    def test_emergency_intent_mapping(self):
        pkt = response_to_uscp("halt", target_id="x", original_intent="EMERGENCY_HALT")
        assert pkt["body"]["intent"] == "EMERGENCY_ACK"
        assert pkt["header"]["priority"] == "CRITICAL"

    def test_handshake_intent_mapping(self):
        pkt = response_to_uscp("ack", target_id="x", original_intent="HANDSHAKE_COMPLETE")
        assert pkt["body"]["intent"] == "HANDSHAKE_COMPLETE"
        assert pkt["header"]["priority"] == "HIGH"

    def test_reasoning_intent_mapping(self):
        pkt = response_to_uscp("because", target_id="x", original_intent="REQUEST_REASONING")
        assert pkt["body"]["intent"] == "REASONING_RESPONSE"

    def test_query_intent_mapping(self):
        pkt = response_to_uscp("answer", target_id="x", original_intent="QUERY")
        assert pkt["body"]["intent"] == "QUERY_RESPONSE"

    def test_unknown_intent_falls_back(self):
        pkt = response_to_uscp("ok", target_id="x", original_intent="WAT")
        assert pkt["body"]["intent"] == "WESLEY_RESPONSE"

    def test_response_contains_text(self):
        pkt = response_to_uscp("I am fine.", target_id="x")
        data = pkt["body"]["payload"]["data"]
        assert data["response"] == "I am fine."

    def test_timestamp_is_iso(self):
        pkt = response_to_uscp("x", target_id="x")
        ts = pkt["header"]["timestamp"]
        # ISO-8601 basic sanity
        assert "T" in ts
        assert ts.endswith("+00:00") or ts.endswith("Z")


# ---- build_ollama_request ----

class TestBuildOllamaRequest:
    def test_model_set(self):
        req = build_ollama_request([], model="granite3-dense:2b")
        assert req["model"] == "granite3-dense:2b"

    def test_default_model(self):
        req = build_ollama_request([])
        assert req["model"] == "granite3-dense:8b"

    def test_stream_false_by_default(self):
        req = build_ollama_request([])
        assert req["stream"] is False

    def test_temperature_in_options(self):
        req = build_ollama_request([], temperature=0.3)
        assert req["options"]["temperature"] == 0.3

    def test_messages_passed_through(self):
        msgs = [{"role": "system", "content": "hi"}]
        req = build_ollama_request(msgs)
        assert req["messages"] is msgs


# ---- OllamaMessage ----

class TestOllamaMessage:
    def test_to_dict(self):
        msg = OllamaMessage("user", "hello")
        assert msg.to_dict() == {"role": "user", "content": "hello"}

    def test_roles(self):
        for role in ("system", "user", "assistant"):
            msg = OllamaMessage(role, "x")
            assert msg.role == role
