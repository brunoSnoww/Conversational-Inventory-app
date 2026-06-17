from __future__ import annotations

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from ai.history import rows_to_message_history


def test_rows_to_message_history_alternating_roles():
    rows = [
        {"role": "user", "content": "how much stock of CB-01?"},
        {"role": "assistant", "content": "You have 50 units on hand."},
        {"role": "user", "content": "sell 10 at $5 each"},
    ]
    history = rows_to_message_history(rows)
    assert len(history) == 3
    assert isinstance(history[0], ModelRequest)
    assert history[0].parts[0].content == "how much stock of CB-01?"
    assert isinstance(history[1], ModelResponse)
    assert history[1].parts[0].content == "You have 50 units on hand."
    assert isinstance(history[2], ModelRequest)


def test_rows_to_message_history_skips_empty_content():
    rows = [
        {"role": "user", "content": "   "},
        {"role": "assistant", "content": "ok"},
    ]
    history = rows_to_message_history(rows)
    assert len(history) == 1
    assert isinstance(history[0], ModelResponse)
    assert isinstance(history[0].parts[0], TextPart)
