"""Local filesystem storage client for Chainlit file uploads.

Implements Chainlit's BaseStorageClient interface using the local filesystem,
eliminating the need for S3/GCS/Azure in development. Files are stored under
a configurable directory and served via a ``/local-files/`` HTTP endpoint
registered at import time so that replayed threads can load file attachments.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiofiles
from chainlit.data.storage_clients.base import BaseStorageClient

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_PATH = ".chainlit/data/files"


class LocalStorageClient(BaseStorageClient):
    """Store uploaded files on the local filesystem."""

    def __init__(self, storage_path: str = _DEFAULT_STORAGE_PATH) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self,
        object_key: str,
        data: bytes | str,
        mime: str = "application/octet-stream",
        overwrite: bool = True,
        content_disposition: str | None = None,
    ) -> dict[str, Any]:
        """Write file data to local storage."""
        file_path = self.storage_path / object_key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not overwrite and file_path.exists():
            return {"object_key": object_key, "url": str(file_path)}

        mode = "wb" if isinstance(data, bytes) else "w"
        async with aiofiles.open(file_path, mode) as f:
            await f.write(data)

        logger.debug("Stored file: %s (%s)", object_key, mime)
        return {"object_key": object_key, "url": str(file_path)}

    async def delete_file(self, object_key: str) -> bool:
        """Remove a file from local storage."""
        file_path = self.storage_path / object_key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def get_read_url(self, object_key: str) -> str:
        """Return an HTTP-accessible URL served by the local-files endpoint."""
        return f"/local-files/{object_key}"

    async def close(self) -> None:
        """No-op — no connections to close for local filesystem."""


def mount_local_files_endpoint() -> None:
    """Register a ``/local-files/`` GET route on Chainlit's FastAPI app.

    This allows the browser to fetch files stored by ``LocalStorageClient``
    when replaying past conversation threads. Must be called after
    Chainlit's server is initialised (e.g. at the top of ``app.py``).
    """
    from chainlit.server import app as chainlit_app
    from starlette.responses import FileResponse, Response

    storage_root = Path(_DEFAULT_STORAGE_PATH).resolve()

    @chainlit_app.get("/local-files/{file_path:path}")
    async def serve_local_file(file_path: str) -> Response:
        full_path = (storage_root / file_path).resolve()
        # Prevent directory traversal
        if not str(full_path).startswith(str(storage_root)):
            return Response(status_code=403)
        if not full_path.exists():
            return Response(status_code=404)
        return FileResponse(full_path)
