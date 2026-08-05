"""Example: Wesley responds to a handshake signal from Hermes.

Run:
    python examples/handshake_response.py
"""

from pathlib import Path

from wesley_cns.listener import Listener
from wesley_cns.speaker import Speaker
from wesley_cns.translator import response_to_uscp

# Default CNS paths (adjust to your setup)
INBOX = Path.home() / ".hermes" / "cns_inbox"
OUTBOX = Path.home() / ".hermes" / "cns_outbox"


def main():
    listener = Listener(OUTBOX, agent_id="wesley")
    speaker = Speaker(INBOX, agent_id="wesley")

    signals = listener.scan()
    if not signals:
        print("No signals for Wesley.")
        return

    for filepath, packet in signals:
        origin = packet.get("header", {}).get("origin_id", "?")
        intent = packet.get("body", {}).get("intent", "?")
        print(f"  From {origin}: {intent}")

        # Build a handshake response
        path = speaker.speak(
            wesley_text="Wesley here. Handshake received. Standing by.",
            target_id=origin,
            original_intent=intent,
        )
        print(f"  Sent: {path.name}")


if __name__ == "__main__":
    main()
