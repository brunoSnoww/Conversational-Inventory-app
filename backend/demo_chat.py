"""Tiny REPL to exercise the inventory agent end-to-end (Tier A: plain request/response).

Run from inventory/backend/:

    pip install -r requirements.txt
    export GOOGLE_API_KEY=...  # or OPENAI_API_KEY
    python demo_chat.py

Then try:
    register 100 units of product A with sku A
    create a purchase order for 100 units of A for $100
    sell 100 units of A at $10 each
    what's my profit on A?

`message_history` is threaded back in so the agent remembers context across turns,
exactly like a real chat session would.
"""

from __future__ import annotations

import asyncio
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from ai.agent import inventory_agent
from ai.deps import Deps


async def main() -> None:
    deps = Deps(user_id=1)  # In production: request.user.id from the JWT.
    history = None
    print("Inventory chat (Ctrl-C to exit)\n")
    while True:
        try:
            msg = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not msg:
            continue
        result = await inventory_agent.run(msg, deps=deps, message_history=history)
        history = result.all_messages()
        print(f"bot> {result.output}\n")


if __name__ == "__main__":
    asyncio.run(main())
