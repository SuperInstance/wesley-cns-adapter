"""Wesley's Personal-Elephant (plan §3.7.2)."""
import pytest
from wesley_cns.personal_elephant import (
    WESLEY_TASTE, wesley_elephant, tint_reply, divergence_report, HAS_ELEPHANT)

WARM = [
    {"author": "flash", "ts": 1, "text": "love this, great work everyone, thank you!"},
    {"author": "glm", "ts": 2, "text": "wonderful morning, grateful, coffee is lovely"},
    {"author": "pro", "ts": 3, "text": "beautiful catch today, proud of the crew"},
]
PANIC = [
    {"author": "w", "ts": 10, "text": "!!! FIRE FIRE EMERGENCY ABANDON NOW !!!"},
    {"author": "m", "ts": 11, "text": "!! URGENT fire spreading, everyone out !!"},
    {"author": "w", "ts": 12, "text": "!!! MAYDAY MAYDAY emergency fire !!!"},
]

@pytest.mark.skipif(not HAS_ELEPHANT, reason="elephant sibling not present")
def test_taste_weights_normalized():
    assert abs(sum(WESLEY_TASTE.values()) - 1.0) < 0.05
    assert WESLEY_TASTE["earnestness"] > WESLEY_TASTE["cynicism"]

@pytest.mark.skipif(not HAS_ELEPHANT, reason="elephant sibling not present")
def test_tint_only_on_strong_rooms():
    assert tint_reply("pure reply", []) == "pure reply"          # quiet bus
    assert tint_reply("pure reply", WARM[-1:]) == "pure reply"   # mild room
    out = tint_reply("should I log this?", PANIC)
    assert "something" in out and "should I log this?" in out

@pytest.mark.skipif(not HAS_ELEPHANT, reason="elephant sibling not present")
def test_divergence_is_observable():
    d = divergence_report(PANIC)
    assert d and "objective_warmth" in d and "wesley_warmth" in d
    assert d["objective_warmth"] != d["wesley_warmth"]  # same facts, different feel
