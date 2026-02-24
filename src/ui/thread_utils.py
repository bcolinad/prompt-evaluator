"""Thread naming utilities for the Chainlit UI."""

from __future__ import annotations

import logging

import chainlit as cl
from chainlit.data import get_data_layer as _get_dl

logger = logging.getLogger(__name__)

_chat_counter: int = 0


def increment_chat_counter() -> int:
    """Increment and return the per-process chat counter.

    Returns:
        The new counter value.
    """
    global _chat_counter
    _chat_counter += 1
    return _chat_counter


async def _set_thread_name(name: str) -> None:
    """Set a short display name for the current conversation thread.

    Updates the thread name in the data layer and emits an event to
    refresh the sidebar UI immediately. Silently skips if no data layer
    or Chainlit context is available (e.g. during tests).

    Args:
        name: The display name for this conversation thread.
    """
    try:

        data_layer = _get_dl()
        if data_layer is None:
            return

        thread_id = cl.context.session.thread_id
        await data_layer.update_thread(thread_id, name=name)

        await cl.context.emitter.emit(
            "first_interaction",
            {"interaction": name, "thread_id": thread_id},
        )
    except Exception:
        logger.debug("Could not set thread name: %s", name, exc_info=True)
