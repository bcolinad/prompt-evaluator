"""Custom Chainlit data layer with orphaned-thread handling and app-table cleanup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chainlit.data.chainlit_data_layer import ChainlitDataLayer

if TYPE_CHECKING:
    from chainlit.types import ThreadDict

logger = logging.getLogger(__name__)


class CustomDataLayer(ChainlitDataLayer):
    """Extends ChainlitDataLayer with orphaned-thread safety and app-table cleanup.

    **Orphaned-thread handling:**  Threads created before authentication was
    enabled (or during anonymous sessions) may have a ``NULL`` ``userIdentifier``.
    Chainlit's WebSocket connect handler compares ``thread["userIdentifier"]``
    against the authenticated user's identifier and raises
    ``ConnectionRefusedError("authorization failed")`` when they don't match
    — including when ``userIdentifier`` is ``None``.

    This override returns ``None`` for such threads so Chainlit silently starts
    a fresh thread instead of logging a daily ``[ERROR] Authorization for the
    thread failed.`` message.

    **App-table cleanup:**  When a user deletes a chat thread from the sidebar,
    this layer removes related rows from ``evaluations`` and
    ``conversation_embeddings`` before delegating to the parent's
    ``delete_thread``.
    """

    async def get_thread(self, thread_id: str) -> ThreadDict | None:
        """Fetch a thread, returning ``None`` for orphaned threads.

        A thread is considered orphaned when its ``userIdentifier`` is
        ``None`` or empty — this prevents Chainlit's strict ownership check
        from raising an authorization error.

        Args:
            thread_id: The UUID string of the thread to retrieve.

        Returns:
            The ``ThreadDict`` if the thread exists and has a valid owner,
            otherwise ``None``.
        """
        thread = await super().get_thread(thread_id)
        if thread is not None and not thread.get("userIdentifier"):
            logger.warning(
                "Thread %s has no userIdentifier — returning None to avoid "
                "authorization error (orphaned thread from anonymous/pre-auth session)",
                thread_id,
            )
            return None
        return thread

    async def delete_thread(self, thread_id: str) -> None:
        """Delete app data linked to *thread_id*, then delete the Chainlit thread.

        Args:
            thread_id: The UUID string of the Chainlit thread being deleted.
        """
        try:
            await self.execute_query(
                "DELETE FROM document_chunks WHERE thread_id = $1",
                {"thread_id": thread_id},
            )
            await self.execute_query(
                "DELETE FROM documents WHERE thread_id = $1",
                {"thread_id": thread_id},
            )
            await self.execute_query(
                "DELETE FROM conversation_embeddings WHERE thread_id = $1",
                {"thread_id": thread_id},
            )
            await self.execute_query(
                "DELETE FROM evaluations WHERE thread_id = $1",
                {"thread_id": thread_id},
            )
            logger.info("Cleaned up app data for deleted thread %s", thread_id)
        except Exception:
            logger.warning(
                "Failed to clean up app data for thread %s, proceeding with thread deletion",
                thread_id,
                exc_info=True,
            )

        await super().delete_thread(thread_id)
