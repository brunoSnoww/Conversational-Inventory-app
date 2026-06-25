"""Shared agent/chat constants."""

THINKING_PLACEHOLDER = "Thinking…"

# Agent LLM context — last N non-placeholder turns loaded server-side (ai/history.py).
CHAT_HISTORY_LIMIT = 5

# PowerSync stream cap — last N rows replicated to client (powersync/config.yaml).
CHAT_SYNC_LIMIT = 100
