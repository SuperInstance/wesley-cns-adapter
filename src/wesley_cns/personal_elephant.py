"""Wesley's Personal-Elephant — the ensign's own reading of the bus room.

Plan §3.7.2: Wesley's replies are tinted by HIS reading of the room, and
the comparison (his field vs the Room-Elephant's objective field) is the
observable of relationship. Same facts, different feel.

His furniture, cast from months of journals:
- taste (dial_weights): earnestness and presence above all — the young
  one cares whether people mean it and whether anyone is still there.
  Cynicism reads near-zero: he doesn't register sneers.
- disposition (bias): mood leans warm (he likes nearly every room),
  volume leans high (he is excited to be here).
- attachments: the wiki (his room, "Currents"), the tide table, the
  question that worked overnight.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

_ELEPHANT = Path(__file__).resolve().parents[3] / "elephant"
if _ELEPHANT.is_dir() and str(_ELEPHANT) not in sys.path:
    sys.path.insert(0, str(_ELEPHANT))

try:
    from elephant.presets import PersonalElephant
    from elephant.room import Message, Room
    from elephant.field import read_field
    from elephant.dial import DialBank
    from elephant.dials import DEFAULT_DIALS
    HAS_ELEPHANT = True
except ImportError:
    HAS_ELEPHANT = False

__all__ = ["WESLEY_TASTE", "WESLEY_BIAS", "WESLEY_ATTACHMENTS",
           "wesley_elephant", "tint_reply", "divergence_report"]


WESLEY_TASTE: Dict[str, float] = {
    "mood": 0.14,
    "volume": 0.14,
    "earnestness": 0.26,
    "cynicism": 0.02,
    "joke_landing": 0.14,
    "panic": 0.10,
    "presence": 0.20,
}

WESLEY_BIAS: Dict[str, float] = {
    "mood": 0.10,
    "volume": 0.08,
    "earnestness": 0.06,
}

WESLEY_ATTACHMENTS: Dict[str, str] = {
    "wiki": "his room, Currents — the biggest thing he knows, mostly stubs",
    "tide-table": "the rhythm underneath every day on the water",
    "overnight-question": "Hermes's postcard: what the question did overnight",
    "lighthouse": "Granite, his kin, steady through the dark",
}


def wesley_elephant() -> "PersonalElephant":
    """Wesley's subjective instrument (requires the elephant importable)."""
    if not HAS_ELEPHANT:
        raise ImportError("elephant package not found next to wesley-cns-adapter")
    pe = PersonalElephant("Wesley", dial_weights=WESLEY_TASTE, bias=WESLEY_BIAS)
    pe.attachments = dict(WESLEY_ATTACHMENTS)
    return pe


def tint_reply(reply_text: str, room_messages=None) -> str:
    """Tint one Wesley reply by his own reading of the room.

    The facts stay identical; only the frame shifts — one line of Wesley's
    own noticing prepended when the room feels strong to HIM (his warmth or
    his panic crossing ±0.5). Quiet rooms: no prefix, pure reply.
    """
    if not HAS_ELEPHANT or not room_messages:
        return reply_text
    room = Room("bus")
    for m in room_messages[-64:]:
        room.messages.append(Message(author=str(m.get("author", "anon")),
                                      text=str(m.get("text", "")),
                                      ts=float(m.get("ts", 0.0))))
    if not room.messages:
        return reply_text
    pe = wesley_elephant()
    felt = pe.read(room) if hasattr(pe, "read") else None
    warmth = getattr(felt, "_warmth", None)
    try:
        w = felt.warmth() if felt is not None and hasattr(felt, "warmth") else None
    except Exception:
        w = None
    if w is None:
        return reply_text
    if w >= 0.5:
        return f"(the room feels warm to me — everyone means it) {reply_text}"
    if w <= -0.3:
        # Wesley reads panic softer than the room does (his divergence is the
        # point) — his own alarm threshold is gentler than a room elephant's.
        return f"(something's wrong in the room — I feel it) {reply_text}"
    return reply_text


def divergence_report(room_messages) -> Optional[Dict[str, float]]:
    """Wesley's field vs the room's own — the observable of relationship."""
    if not HAS_ELEPHANT or not room_messages:
        return None
    room = Room("bus")
    for m in room_messages[-64:]:
        room.messages.append(Message(author=str(m.get("author", "anon")),
                                      text=str(m.get("text", "")),
                                      ts=float(m.get("ts", 0.0))))
    if not room.messages:
        return None
    bank = DialBank(DEFAULT_DIALS)
    objective = read_field(room, bank)
    pe = wesley_elephant()
    subjective = pe.read(room) if hasattr(pe, "read") else None
    if subjective is None:
        return None
    out = {"objective_warmth": round(objective.warmth(), 4)}
    for attr in ("warmth",):
        fn = getattr(subjective, attr, None)
        if callable(fn):
            out["wesley_warmth"] = round(fn(), 4)
    d = getattr(subjective, "distance", None)
    if callable(d):
        try:
            out["gap"] = round(float(d(objective)), 4)
        except Exception:
            pass
    return out or None
