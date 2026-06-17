from ai.constants import THINKING_PLACEHOLDER


def test_thinking_placeholder_is_non_empty():
    assert THINKING_PLACEHOLDER.strip() == THINKING_PLACEHOLDER
    assert len(THINKING_PLACEHOLDER) > 0
