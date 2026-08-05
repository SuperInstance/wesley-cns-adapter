# 🧠 Wesley CNS Adapter

Connects **Wesley** (IBM Granite via Ollama) to the **CNS signal bus**. Wesley can receive USCP signals from other agents and respond through the CNS inbox.

## Architecture

```
                    CNS Signal Bus
                    ┌─────────────────────────┐
                    │  cns_inbox   cns_outbox  │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──────────▼────────┐
                    │    Wesley CNS Adapter     │
                    │                           │
                    │  Listener → Translator    │
                    │      ↓         ↑          │
                    │  Ollama API (Granite)     │
                    │      ↓                   │
                    │  Speaker → cns_inbox      │
                    └───────────────────────────┘
```

## How It Works

1. **Listener** polls `cns_outbox` for new USCP signals
2. **Translator** converts USCP packets into natural-language chat messages
3. Wesley (Granite via Ollama) generates a response
4. **Speaker** wraps the response in a USCP packet and drops it in `cns_inbox`

## Prerequisites

- [Ollama](https://ollama.ai) running locally with a Granite model:
  ```bash
  ollama pull granite3-dense:8b
  ```

## Install

```bash
pip install -e .
```

## Usage

```bash
# Process current unread signals once
wesley-cns

# Watch mode — continuously listen and respond
wesley-cns --watch

# Custom Ollama host/port
wesley-cns --watch --ollama-host 192.168.1.100 --ollama-port 11434

# Different model
wesley-cns --watch --model granite3-dense:2b

# Dry run — see Wesley's responses without sending them
wesley-cns --dry-run

# Custom poll interval
wesley-cns --watch --interval 0.5
```

## Signal Flow

When Wesley receives a signal like:

```json
{
  "header": {"origin_id": "hermes-cns", "priority": "HIGH", ...},
  "body": {"intent": "REQUEST_REASONING", "payload": {...}}
}
```

It translates this into a chat prompt, queries Granite, and responds:

```json
{
  "header": {"origin_id": "wesley", "priority": "HIGH", ...},
  "body": {
    "intent": "REASONING_RESPONSE",
    "payload": {
      "type": "agent_response",
      "data": {"agent": "wesley", "model": "granite", "response": "..."}
    }
  }
}
```

## License

MIT
